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
        """Scrapes the live market table for Price and Volume."""
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

    def fetch_top_brokers(self):
        """Scrapes Top Brokers and ranks them 1, 2, 3 by Buying Volume/Amount."""
        try:
            url = "https://www.sharesansar.com/top-brokers"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            broker_list = []
            if table:
                rows = table.find_all('tr')
                # Grab Top 3 rows
                for i, row in enumerate(rows[1:4], 1):
                    cols = row.find_all('td')
                    if len(cols) > 3:
                        name = cols[2].text.strip().split(' ')[0] # Shorter name
                        buy_vol = cols[3].text.strip()
                        broker_list.append(f"**{i}: {name}** — {buy_vol}")
            return "\n".join(broker_list) if broker_list else "Waiting for market activity..."
        except:
            return "Broker data temporarily offline."

    async def setup_hook(self):
        data = self.fetch_nepse_table()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
        self.alert_engine.start()

    @tasks.loop(seconds=30)
    async def alert_engine(self):
        if not self.active_alerts: return
        live_data = self.fetch_nepse_table()
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

@bot.tree.command(name="price", description="LTP, Volume, Pressure & Top Brokers")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_nepse_table()
    
    if sym in data:
        stock = data[sym]
        broker_ranking = bot.fetch_top_brokers()
        
        # Calculate Pressure
        change_f = float(stock['change'].replace('+', ''))
        pressure = "🟢 Buying Pressure" if change_f > 0 else "🔴 Selling Pressure" if change_f < 0 else "⚖️ Neutral"
        color = 0x2ecc71 if change_f > 0 else 0xe74c3c if change_f < 0 else 0x34495e
        
        embed = discord.Embed(title=f"📊 {sym} Market Report", color=color)
        embed.add_field(name="Current Price", value=f"**Rs. {stock['ltp']}** ({stock['change']})", inline=True)
        embed.add_field(name="Volume", value=f"{stock['vol']} units", inline=True)
        embed.add_field(name="Market Pressure", value=f"**{pressure}**", inline=False)
        embed.add_field(name="🏆 Top 3 Buying Brokers (Today)", value=broker_ranking, inline=False)
        embed.set_footer(text="Data: Sharesansar Live Feed • 2026")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Market closed or symbol **{sym}** not found. Check back at 10:30 AM NST.")

@bot.tree.command(name="sync_symbols", description="Refresh the search list")
async def sync_symbols(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.fetch_nepse_table()
    if data:
        bot.all_symbols = sorted(list(data.keys()))
        await interaction.followup.send(f"✅ Synced {len(bot.all_symbols)} stocks!")
    else:
        await interaction.followup.send("⚠️ Table empty. Try at 10:30 AM.")

@price.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not bot.all_symbols: return []
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
