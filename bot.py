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
        self.all_symbols = []
        self.active_alerts = {} 

    def fetch_live_market(self):
        """Directly scrapes the main live trading table."""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            
            data_map = {}
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 7:
                        sym = cols[1].text.strip()
                        data_map[sym] = {
                            "ltp": cols[2].text.strip().replace(',', ''),
                            "change": cols[3].text.strip(),
                            "vol": cols[7].text.strip().replace(',', '')
                        }
            return data_map
        except:
            return {}

    async def setup_hook(self):
        # Dynamically load symbols for the search bar
        data = self.fetch_live_market()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL", "HIDCL"]
        await self.tree.sync()
        if not self.alert_engine.is_running():
            self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"🚨 <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=30)
    async def alert_engine(self):
        if not self.active_alerts: return
        live_data = self.fetch_live_market()
        
        for user_id, config in list(self.active_alerts.items()):
            sym = config['symbol']
            if sym in live_data:
                try:
                    current_p = float(live_data[sym]['ltp'])
                    if current_p <= config['low']:
                        msg = f"PRICE DROPPED! {sym} is at Rs. {current_p}"
                        del self.active_alerts[user_id]
                        await self.fire_pings(user_id, config['channel'], msg, 5)
                    elif current_p >= config['high']:
                        msg = f"BREAKOUT! {sym} is at Rs. {current_p}"
                        del self.active_alerts[user_id]
                        await self.fire_pings(user_id, config['channel'], msg, 7)
                except: continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Live NEPSE Price with Fail-Safe Scraper")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    all_data = bot.fetch_live_market()
    
    if sym in all_data:
        stock = all_data[sym]
        ltp = stock['ltp']
        change = stock['change']
        vol = stock['vol']
        
        color = 0x2ecc71 if "+" in change or (change != "0" and "-" not in change) else 0xe74c3c if "-" in change else 0x34495e
        embed = discord.Embed(title=f"📊 {sym} Live Analysis", color=color)
        embed.add_field(name="Current Price", value=f"**Rs. {ltp}**", inline=True)
        embed.add_field(name="Point Change", value=f"{change}", inline=True)
        embed.add_field(name="Total Volume", value=f"{vol}", inline=False)
        embed.set_footer(text="Data: Sharesansar Live Feed • Backup Engine Active")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Market data for **{sym}** is currently unavailable. The market might be closed or the symbol is hidden.")

@bot.tree.command(name="set_alert", description="Targets: 5x pings for Low, 7x for High")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {"symbol": sym, "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**! I'll watch the live table for you.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
