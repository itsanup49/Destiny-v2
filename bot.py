import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, asyncio, requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

# --- BRANDING ---
BOT_NAME = "Destiny NEPSE"
FOOTER = "Destiny Analytics • Live Market Intelligence"
COLOR_MAIN = 0x5865F2

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.all_symbols = []
        self.active_alerts = {}

    def fetch_soup(self, url):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return BeautifulSoup(res.text, 'html.parser')
        except: return None

    def fetch_live_data(self):
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

    def fetch_broker_ranking(self):
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
        return "\n".join(ranking) if ranking else "No broker data."

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
                        status = cols[8].text.strip()
                        issues.append(f"📌 **{comp}** (Ends: {status})")
        return "\n".join(issues) if issues else "No active IPOs."

    async def setup_hook(self):
        data = self.fetch_live_data()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA"]
        await self.tree.sync()

bot = DestinyBot()

@bot.tree.command(name="stonk", description="Full details: LTP, Volume, Pressure & Brokers")
async def stonk(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_live_data()
    if sym in data:
        stock = data[sym]
        brokers = bot.fetch_broker_ranking()
        change_f = float(stock['change'].replace('+', ''))
        color = 0x2ecc71 if change_f > 0 else 0xe74c3c if change_f < 0 else 0x34495e
        
        embed = discord.Embed(title=f"📈 {sym} Market Analysis", color=color)
        embed.add_field(name="Price", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Change", value=f"`{stock['change']}`", inline=True)
        embed.add_field(name="Volume", value=f"`{stock['vol']}`", inline=True)
        embed.add_field(name="🏆 Top 3 Brokers", value=brokers, inline=False)
        embed.set_footer(text=FOOTER)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ {sym} not found. Market may be closed.")

@bot.tree.command(name="ipo", description="Check active IPOs and Right Shares")
async def ipo(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.get_ipos()
    embed = discord.Embed(title=f"🚀 Active IPOs | {BOT_NAME}", description=data, color=COLOR_MAIN)
    embed.set_footer(text=FOOTER)
    await interaction.followup.send(embed=embed)

@stonk.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
