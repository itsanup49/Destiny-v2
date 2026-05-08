import discord
from discord.ext import commands
from discord import app_commands
import aiohttp # Using aiohttp for faster, non-blocking requests
from .utils import ALL_SYMBOLS, get_nepal_time

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25]

    @app_commands.command(name="stock", description="Get live stock price via ShareBazaar API")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()
        
        # ShareBazaar API endpoint
        api_url = f"https://nepsetty.kokomo.workers.dev/api?symbol={sym}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extracting clean data from API response
                        ltp = data.get('currentPrice', 'N/A')
                        change = data.get('change', '0')
                        percent = data.get('percentChange', '0%')
                        volume = data.get('volume', 'N/A')
                        
                        # Color coding
                        color = 0x2ecc71 if float(str(change).replace(',', '')) >= 0 else 0xe74c3c
                        
                        embed = discord.Embed(title=f"📈 {sym} | API Live Data", color=color)
                        embed.add_field(name="LTP (Rs.)", value=f"**{ltp}**", inline=True)
                        embed.add_field(name="Change (%)", value=f"`{change} ({percent})`", inline=True)
                        embed.add_field(name="Volume", value=f"{volume}", inline=True)
                        embed.set_footer(text="Data sourced via ShareBazaar API")
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(f"❌ API Error: Symbol **{sym}** not found or service down.")
            except Exception as e:
                await interaction.followup.send(f"❌ Connection Error: Could not reach the data server.")

async def setup(bot):
    await bot.add_cog(Market(bot))
