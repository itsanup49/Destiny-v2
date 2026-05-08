import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ipo", description="Check current IPOs")
    async def ipo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("🚀 Fetching IPO data...")

    @app_commands.command(name="chart", description="View stock chart")
    async def chart(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        await interaction.followup.send(f"📊 Generating chart for {symbol.upper()}...")

async def setup(bot):
    await bot.add_cog(Tools(bot))
