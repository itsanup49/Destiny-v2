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

    def fetch_nepse_table(self):
        """This is the scraper logic. It reads the live table like a browser."""
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
        # Fill the autocomplete list on startup
        data = self.fetch_nepse_table()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
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
        live_data = self.fetch_nepse_table()
        for user_id, config in list(self.active_alerts.items()):
            sym = config['symbol']
            if sym in live_data:
                try:
                    price = float(live_data[sym]['ltp'])
                    if price <= config['low']:
                        await self.fire_pings(user_id, config['channel'], f"{sym} hit Low Target: {price}", 5)
                        del self.active_alerts[user_id]
                    elif price >= config['high']:
                        await self.fire_pings(user_id, config['channel'], f"{sym} hit High Target: {price}", 7)
                        del self.active_alerts[user_id]
                except: continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live price from Sharesansar")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_nepse_table()
    if sym in data:
        stock = data[sym]
        embed = discord.Embed(title=f"📊 {sym} Live", color=0x2ecc71)
        embed.add_field(name="LTP", value=f"Rs. {stock['ltp']}")
        embed.add_field(name="Change", value=stock['change'])
        embed.set_footer(text="Source: Sharesansar Live Table")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Could not find {sym} in the live table.")

@bot.tree.command(name="set_alert")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    bot.active_alerts[interaction.user.id] = {"symbol": symbol.upper(), "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert set for {symbol.upper()}!")

bot.run(TOKEN)
