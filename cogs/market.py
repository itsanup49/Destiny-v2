import discord
from discord.ext import commands
from discord import app_commands
from .utils import ALL_SYMBOLS, get_nepal_time # Use the full list

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # This handles the search as the user types
    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        # Only show the top 25 matches (Discord's maximum limit)
        matches = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return matches[:25] 

    @app_commands.command(name="stock", description="Check any NEPSE stock")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        # (Rest of your scraping logic for today-price goes here...)
        await interaction.followup.send(f"Fetching {symbol}...")

async def setup(bot):
    await bot.add_cog(Market(bot))
