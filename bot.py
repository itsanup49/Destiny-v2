import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        # We will populate this list dynamically from the live table
        self.all_symbols = []
        self.active_alerts = {} 

    def get_all_live_data(self):
        """Fetches the entire live market table from Sharesansar."""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            
            data_map = {}
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]: # Skip header
                    cols = row.find_all('td')
                    if len(cols) > 7:
                        sym = cols[1].text.strip()
                        data_map[sym] = {
                            "ltp": cols[2].text.strip().replace(',', ''),
                            "change": cols[3].text.strip(),
                            "vol": cols[7].text.strip().replace(',', '')
                        }
            return data_map
        except Exception as e:
            print(f"Scrape Error: {e}")
            return {}

    async def setup_hook(self):
        # Initial pull to get symbols for autocomplete
        data = self.get_all_live_data()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
        self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"🚨 <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=20)
    async def alert_engine(self):
        if not self.active_alerts: return
        live_data = self.get_all_live_data()
        
        for user_id, config in list(self.active_alerts.items()):
            sym = config['symbol']
            if sym in live_data:
                current_p = float(live_data[sym]['ltp'])
                if current_p <= config['low']:
                    msg = f"PRICE DROPPED! {sym} is at Rs. {current_p}"
                    del self.active_alerts[user_id]
                    await self.fire_pings(user_id, config['channel'], msg, 5)
                elif current_p >= config['high']:
                    msg = f"BREAKOUT! {sym} is at Rs. {current_p}"
                    del self.active_alerts[user_id]
                    await self.fire_pings(user_id, config['channel'], msg, 7)

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live LTP from Sharesansar")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    all_data = bot.get_all_live_data()
    
    if sym in all_data:
        stock = all_data[sym]
        ltp = stock['ltp']
        change = stock['change']
        vol = stock['vol']
        
        color = 0x2ecc71 if float(change) > 0 else 0xe74c3c if float(change) < 0 else 0x34495e
        embed = discord.Embed(title=f"📊 {sym} Live Data", color=color)
        embed.add_field(name="LTP", value=f"**Rs. {ltp}**", inline=True)
        embed.add_field(name="Change", value=f"{change}", inline=True)
        embed.add_field(name="Volume", value=f"{vol}", inline=False)
        embed.set_footer(text="Source: Sharesansar Live Table")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ {sym} not found in live table. Market might be closed or symbol is wrong.")

@bot.tree.command(name="set_alert", description="Alerts: 5x for Low, 7x for High")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {"symbol": sym, "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**!")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not bot.all_symbols:
        data = bot.get_all_live_data()
        bot.all_symbols = sorted(list(data.keys()))
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
