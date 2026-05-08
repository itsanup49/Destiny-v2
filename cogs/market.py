import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
from .utils import ALL_SYMBOLS, get_nepal_time

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=s, value=s) for s in ALL_SYMBOLS if current.upper() in s.upper()][:25]

    @app_commands.command(name="stock", description="Check stock price")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        try:
            url = f"https://www.sharesansar.com/today-price"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            # Data extraction logic here
            await interaction.followup.send(f"📊 {symbol.upper()} data fetched.")
        except:
            await interaction.followup.send("❌ Error fetching data.")

    @app_commands.command(name="nepse", description="Get NEPSE status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        _, status = get_nepal_time()
        await interaction.followup.send(f"📈 NEPSE Status: {status}")

async def setup(bot):
    await bot.add_cog(Market(bot))
