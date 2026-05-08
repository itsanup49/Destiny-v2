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
        """Scrapes the live market table."""
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
        """Scrapes the Top Brokers page for today's highest buyers."""
        try:
            url = "https://www.sharesansar.com/top-brokers"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            brokers = []
            if table:
                rows = table.find_all('tr')
                for row in rows[1:4]: # Top 3 only
                    cols = row.find_all('td')
                    if len(cols) > 3:
                        name = cols[2].text.strip().replace('Co. Ltd.', '').replace('Pvt. Limited', '')
                        buy_amt = cols[3].text.strip()
                        brokers.append(f"**{len(brokers)+1}.** {name[:15]}... (Rs. {buy_amt})")
            return "\n".join(brokers) if brokers else "No broker data yet today."
        except:
            return "Broker data currently unavailable."

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
                        # Simplified alert ping
                        channel = self.get_channel(config['channel'])
                        if channel: await channel.send(f"🚨 <@{user_id}> {sym} hit Target: {price}")
                        del self.active_alerts[user_id]
                except: continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP and Top 3 Buying Brokers")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_nepse_table()
    
    if sym in data:
        stock = data[sym]
        broker_text = bot.fetch_top_brokers() # Get broker ranking
        
        color = 0x2ecc71 if "+" in stock['change'] else 0xe74c3c if "-" in stock['change'] else 0x34495e
        embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
        embed.add_field(name="Current Price", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Change", value=stock['change'], inline=True)
        embed.add_field(name="🏆 Top Buyers (Market-wide)", value=broker_text, inline=False)
        embed.set_footer(text="Broker data reflects total market buying today.")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Market closed or symbol **{sym}** not found.")

@bot.tree.command(name="sync_symbols")
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
