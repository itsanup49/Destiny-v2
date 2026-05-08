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
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25]

    @app_commands.command(name="stock", description="Live price for any NEPSE stock")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()
        
        try:
            # We use the mobile-friendly 'today-price' URL which is more stable for scraping
            url = "https://www.sharesansar.com/today-price"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', {'id': 'headertfixed'}) or soup.find('table')
            
            data = None
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    # Search specifically in the 2nd column (Symbol)
                    if len(cols) > 1 and cols[1].text.strip().upper() == sym:
                        data = {
                            "ltp": cols[6].text.strip().replace(',', ''),
                            "chg": cols[10].text.strip(),
                            "vol": cols[8].text.strip()
                        }
                        break

            if data:
                # Handle color based on point change
                try:
                    change_val = float(data['chg'].replace(',', ''))
                    color = 0x2ecc71 if change_val > 0 else (0xe74c3c if change_val < 0 else 0x95a5a6)
                except:
                    color = 0x3498db

                embed = discord.Embed(title=f"📈 {sym} | Real-Time Data", color=color)
                embed.add_field(name="LTP (Rs.)", value=f"**{data['ltp']}**", inline=True)
                embed.add_field(name="Change", value=f"`{data['chg']}`", inline=True)
                embed.add_field(name="Volume", value=data['vol'], inline=True)
                embed.set_footer(text=f"Requested by {interaction.user.name}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ **{sym}** not found in today's price list. The market might be updating or the symbol is incorrect.")
        except Exception as e:
            await interaction.followup.send(f"❌ Scraper Error: ShareSansar is currently unreachable.")

    @app_commands.command(name="nepse", description="Check NEPSE status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        t, status = get_nepal_time()
        await interaction.followup.send(f"📊 **NEPSE Status:** {status}\n🕒 **Nepal Time:** {t}")

async def setup(bot):
    await bot.add_cog(Market(bot))
