import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
from .utils import ALL_SYMBOLS, get_nepal_time

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # The Autocomplete search logic
    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        # This filters the 300+ list based on what the user types
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25] # Discord only allows 25 suggestions at a time

    @app_commands.command(name="stock", description="Live price with 300+ stock autocomplete")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()
        
        # Scraper for the actual data
        try:
            url = f"https://www.sharesansar.com/today-price"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            
            stock_data = None
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 1 and cols[1].text.strip() == sym:
                        stock_data = {
                            "ltp": cols[6].text.strip(),
                            "chg": cols[10].text.strip(),
                            "vol": cols[8].text.strip()
                        }
                        break

            if stock_data:
                color = 0x2ecc71 if "+" in stock_data['chg'] or float(stock_data['chg']) > 0 else 0xe74c3c
                embed = discord.Embed(title=f"📊 {sym} | Destiny V2", color=color)
                embed.add_field(name="LTP (Rs.)", value=f"**{stock_data['ltp']}**", inline=True)
                embed.add_field(name="Change", value=f"`{stock_data['chg']}`", inline=True)
                embed.add_field(name="Volume", value=stock_data['vol'], inline=True)
                embed.set_footer(text="Destiny Analytics • 24/7 Data")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Could not find data for **{sym}**.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="nepse", description="Check NEPSE status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        time_now, status = get_nepal_time()
        await interaction.followup.send(f"📈 **NEPSE Status:** {status}\n🕒 **Nepal Time:** {time_now}")

async def setup(bot):
    await bot.add_cog(Market(bot))
