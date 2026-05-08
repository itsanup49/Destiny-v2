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
        # This will now always have at least the backup symbols
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25]

    @app_commands.command(name="stock", description="Check NEPSE stock price")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()
        
        try:
            url = "https://www.sharesansar.com/today-price"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            
            data = None
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 1 and cols[1].text.strip() == sym:
                        data = {"ltp": cols[6].text.strip(), "chg": cols[10].text.strip(), "vol": cols[8].text.strip()}
                        break

            if data:
                # Green color if price is up, Red if down
                color = 0x2ecc71 if "+" in data['chg'] or (data['chg'] != '0' and "-" not in data['chg']) else 0xe74c3c
                embed = discord.Embed(title=f"📊 {sym} | Destiny V2", color=color)
                embed.add_field(name="LTP", value=f"**Rs. {data['ltp']}**", inline=True)
                embed.add_field(name="Change", value=f"`{data['chg']}`", inline=True)
                embed.add_field(name="Volume", value=data['vol'], inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Data for **{sym}** not found. Is the symbol correct?")
        except:
            await interaction.followup.send("❌ Sharesansar is not responding. Try again later.")

    @app_commands.command(name="nepse", description="Check market status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        t, status = get_nepal_time()
        await interaction.followup.send(f"📈 **Status:** {status} | 🕒 **NST:** {t}")

async def setup(bot):
    await bot.add_cog(Market(bot))
