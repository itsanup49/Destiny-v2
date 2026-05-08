import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, asyncio, requests, io
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd

# --- BRANDING ---
BOT_NAME = "Destiny NEPSE"
FOOTER = "Destiny Analytics • Live Intelligence"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.all_symbols = []

    def fetch_soup(self, url):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return BeautifulSoup(res.text, 'html.parser')
        except: return None

    # --- DATA SCRAPERS ---
    def fetch_live_market(self):
        soup = self.fetch_soup("https://www.sharesansar.com/live-trading")
        data = {}
        if soup:
            table = soup.find('table', {'id': 'headertall'})
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 7:
                        sym = cols[1].text.strip()
                        data[sym] = {
                            "ltp": cols[2].text.strip().replace(',', ''),
                            "change": cols[3].text.strip(),
                            "vol": cols[7].text.strip().replace(',', '')
                        }
        return data

    def fetch_top_brokers(self):
        soup = self.fetch_soup("https://www.sharesansar.com/top-brokers")
        ranking = []
        if soup:
            table = soup.find('table')
            if table:
                for i, row in enumerate(table.find_all('tr')[1:4], 1):
                    cols = row.find_all('td')
                    if len(cols) > 3:
                        name = cols[2].text.strip().split(' ')[0]
                        vol = cols[3].text.strip()
                        ranking.append(f"**{i}: {name}** — {vol}")
        return "\n".join(ranking) if ranking else "No broker data yet."

    def get_ipos(self):
        soup = self.fetch_soup("https://www.sharesansar.com/existing-issues")
        issues = []
        if soup:
            table = soup.find('table', {'class': 'table'})
            if table:
                for row in table.find_all('tr')[1:6]:
                    cols = row.find_all('td')
                    if len(cols) > 5:
                        comp = cols[2].text.strip()
                        date = cols[8].text.strip()
                        issues.append(f"📌 **{comp}**\n   Ends: {date}")
        return "\n".join(issues) if issues else "No active IPOs."

    # --- CHART GENERATOR ---
    def generate_chart(self, symbol, current_price):
        # We generate a simulated trend based on current price for visual effect
        # In a real environment, you'd pull historical pandas data here
        plt.style.use('dark_background')
        plt.figure(figsize=(8, 4))
        prices = [float(current_price) * (1 + (i*0.01)) for i in range(-5, 1)] # Sample trend
        plt.plot(prices, marker='o', color='#5865F2', linewidth=3)
        plt.fill_between(range(len(prices)), prices, color='#5865F2', alpha=0.2)
        plt.title(f"{symbol} Trend Analysis | {BOT_NAME}")
        plt.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf

    async def setup_hook(self):
        data = self.fetch_live_market()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()

bot = DestinyBot()

@bot.tree.command(name="stonk", description="Price, Volume, Pressure, Brokers & Trend Chart")
async def stonk(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    market = bot.fetch_live_market()
    
    if sym in market:
        stock = market[sym]
        brokers = bot.fetch_top_brokers()
        
        # Logic for Pressure & Color
        change_f = float(stock['change'].replace('+', ''))
        color = 0x2ecc71 if change_f > 0 else 0xe74c3c if change_f < 0 else 0x34495e
        pressure = "🔥 Buying" if change_f > 0 else "❄️ Selling" if change_f < 0 else "Neutral"
        
        # Create Chart
        chart_file = bot.generate_chart(sym, stock['ltp'])
        discord_file = discord.File(chart_file, filename="chart.png")

        embed = discord.Embed(title=f"📊 {sym} Market Dashboard", color=color)
        embed.add_field(name="Current LTP", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Point Change", value=f"`{stock['change']}`", inline=True)
        embed.add_field(name="Volume", value=f"`{stock['vol']} Units`", inline=True)
        embed.add_field(name="Sentiment", value=f"**{pressure}**", inline=True)
        embed.add_field(name="🏆 Top 3 Brokers (Buying)", value=brokers, inline=False)
        embed.set_image(url="attachment://chart.png")
        embed.set_footer(text=FOOTER)
        
        await interaction.followup.send(file=discord_file, embed=embed)
    else:
        await interaction.followup.send(f"❌ Data for {sym} is unavailable right now.")

@bot.tree.command(name="ipo", description="Check current IPOs/Right Shares")
async def ipo(interaction: discord.Interaction):
    await interaction.response.defer()
    issues = bot.get_ipos()
    embed = discord.Embed(title=f"🚀 Active Issues | {BOT_NAME}", description=issues, color=0x5865F2)
    embed.set_footer(text=FOOTER)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="sync", description="Refresh the database")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.fetch_live_market()
    if data:
        bot.all_symbols = sorted(list(data.keys()))
        await interaction.followup.send(f"✅ Synced {len(bot.all_symbols)} Stocks.")
    else:
        await interaction.followup.send("⚠️ Market closed. Try at 10:30 AM.")

@stonk.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
