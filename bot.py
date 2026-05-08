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

    def fetch_live_data(self):
        """Scrapes Sharesansar Live Table for price, volume, and change."""
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
        except: return {}

    def fetch_broker_ranking(self):
        """Scrapes today's Top 3 Brokers by buying volume."""
        try:
            url = "https://www.sharesansar.com/top-brokers"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            ranking = []
            if table:
                rows = table.find_all('tr')
                # Rank top 3
                for i, row in enumerate(rows[1:4], 1):
                    cols = row.find_all('td')
                    if len(cols) > 3:
                        name = cols[2].text.strip().split(' ')[0] # Short name
                        amount = cols[3].text.strip()
                        ranking.append(f"**{i}: {name}** — Rs. {amount}")
            return "\n".join(ranking) if ranking else "No broker data yet."
        except: return "Broker info offline."

    async def setup_hook(self):
        data = self.fetch_live_data()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
        self.alert_engine.start()

    @tasks.loop(seconds=30)
    async def alert_engine(self):
        if not self.active_alerts: return
        live_data = self.fetch_live_data()
        for user_id, config in list(self.active_alerts.items()):
            sym = config['symbol']
            if sym in live_data:
                try:
                    price = float(live_data[sym]['ltp'])
                    if price <= config['low'] or price >= config['high']:
                        channel = self.get_channel(config['channel'])
                        if channel:
                            count = 7 if price >= config['high'] else 5
                            for _ in range(count):
                                await channel.send(f"🚨 <@{user_id}> **{sym}** TARGET HIT: **Rs. {price}**")
                                await asyncio.sleep(3)
                        del self.active_alerts[user_id]
                except: continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Check Price, Volume, Pressure & Broker Rankings")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_live_data()
    
    if sym in data:
        stock = data[sym]
        brokers = bot.fetch_broker_ranking()
        
        # Calculate Pressure & Color
        change_val = float(stock['change'].replace('+', ''))
        pressure = "🟢 Buying Pressure" if change_val > 0 else "🔴 Selling Pressure" if change_val < 0 else "⚖️ Neutral"
        color = 0x2ecc71 if change_val > 0 else 0xe74c3c if change_val < 0 else 0x34495e
        
        embed = discord.Embed(title=f"📊 {sym} Market Dashboard", color=color)
        embed.add_field(name="Current Price (LTP)", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Point Change", value=f"{stock['change']}", inline=True)
        embed.add_field(name="Total Volume", value=f"{stock['vol']} units", inline=False)
        embed.add_field(name="Market Sentiment", value=f"**{pressure}**", inline=True)
        embed.add_field(name="🏆 Top 3 Buying Brokers (Today)", value=brokers, inline=False)
        
        embed.set_footer(text="Data: Sharesansar Live Feed • 2026")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Market data for **{sym}** unavailable. Ensure market is open (11 AM - 3 PM).")

@bot.tree.command(name="sync", description="Force update the symbol list")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.fetch_live_data()
    if data:
        bot.all_symbols = sorted(list(data.keys()))
        await interaction.followup.send(f"✅ Synced {len(bot.all_symbols)} symbols!")
    else:
        await interaction.followup.send("⚠️ Table empty. Try again at 10:30 AM.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)

