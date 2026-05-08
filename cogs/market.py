import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
from .utils import SYMBOLS, get_nepal_time # Import our helpers

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {} # Simple Cache: { "NABIL": {"data": ..., "time": ...} }

    # AUTOCOMPLETE LOGIC
    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=s, value=s)
            for s in SYMBOLS if current.lower() in s.lower()
        ][:25] # Discord limit is 25

    @app_commands.command(name="nepse", description="Get NEPSE Index & Market Status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        time_str, status = get_nepal_time()
        
        # (Scraping logic same as before...)
        embed = discord.Embed(title="📈 NEPSE Index", color=0x5865F2)
        embed.add_field(name="Market Status", value=status, inline=True)
        embed.add_field(name="Time (NST)", value=time_str, inline=True)
        embed.set_footer(text="Destiny Analytics • V2 Pro")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stock", description="Check stock price with Autocomplete")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        # (Data logic same as before...)
        await interaction.followup.send(f"Fetching data for {symbol.upper()}...")

async def setup(bot):
    await bot.add_cog(Market(bot))
