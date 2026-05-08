import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
from .utils import ALL_SYMBOLS, get_nepal_time

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Autocomplete: Shows 300+ stock options as you type
    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ][:25] # Discord limit

    @app_commands.command(name="nepse", description="Check NEPSE Index & Market Status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        time_str, status = get_nepal_time()
        
        # Scrape index data
        try:
            res = requests.get("https://www.sharesansar.com/", headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            # (Scraping logic same as before...)
            
            embed = discord.Embed(title="📈 NEPSE Intelligence", color=0x5865F2)
            embed.add_field(name="Market Status", value=status, inline=True)
            embed.add_field(name="Nepal Time", value=time_str, inline=True)
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send("❌ Error fetching NEPSE index.")

    @app_commands.command(name="stock", description="Live price with 300+ stock autocomplete")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        # Your scraping logic for stock symbols goes here
        await interaction.followup.send(f"🔍 Fetching latest data for **{symbol.upper()}**...")

async def setup(bot):
    await bot.add_cog(Market(bot))
