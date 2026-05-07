import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.live_tracking = {}
        self.all_symbols = ["NABIL", "NICA", "ADBL", "UPPER", "NIFRA", "HIDCL", "HDL"]

    async def get_live_price(self, symbol):
        # Scraping Sharesansar live price page
        url = "https://www.sharesansar.com/live-trading"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finding the row with our symbol
        table = soup.find('table', {'id': 'headertall'})
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) > 0 and cols[1].text.strip() == symbol.upper():
                return float(cols[2].text.replace(',', ''))
        return None

    async def setup_hook(self):
        await self.tree.sync()
        self.market_check_loop.start()

    @tasks.loop(seconds=30)
    async def market_check_loop(self):
        if not self.live_tracking: return
        # Logic to fetch once and update all tracked stocks to save speed
        pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Live NEPSE Price (No Delay)")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        current_price = await bot.get_live_price(sym)
        if current_price:
            embed = discord.Embed(title=f"🔥 {sym} Live", color=discord.Color.gold())
            embed.add_field(name="LTP", value=f"Rs. {current_price}")
            embed.set_footer(text="Source: Sharesansar Live (Real-time)")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Symbol {sym} not found in live trading.")
    except Exception as e:
        await interaction.followup.send("⚠️ Market is likely closed or site is down.")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live with Real-Time Scraping!')

bot.run(TOKEN)
