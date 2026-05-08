import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup

class MarketButtons(discord.ui.View):
    def __init__(self, symbol):
        super().__init__(timeout=60)
        self.symbol = symbol

    @discord.ui.button(label="📊 View Chart", style=discord.ButtonStyle.primary)
    async def chart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Use `/chart symbol:{self.symbol}` to generate the visual trend.", ephemeral=True)

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_247_data(self):
        """Scrapes today-price which keeps data even when market is closed"""
        try:
            url = "https://www.sharesansar.com/today-price"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            data = {}
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 10:
                        sym = cols[1].text.strip()
                        data[sym] = {
                            "ltp": cols[6].text.strip(),  # Close Price
                            "chg": cols[10].text.strip(), # Point Change
                            "vol": cols[8].text.strip()   # Volume
                        }
            return data
        except Exception as e: 
            print(f"Scraper Error: {e}")
            return {}

    @app_commands.command(name="nepse", description="Get the current NEPSE Index status")
    async def nepse(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            res = requests.get("https://www.sharesansar.com/", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Scrape the main index cards from Sharesansar homepage
            index_val = "N/A"
            change_val = "N/A"
            
            # Looking for the NEPSE index block
            indices = soup.find_all('div', class_='index-item')
            for item in indices:
                if 'NEPSE' in item.text:
                    parts = item.text.split()
                    index_val = parts[1]
                    change_val = parts[2]
                    break
            
            color = 0x2ecc71 if "+" in change_val or float(change_val) > 0 else 0xe74c3c
            embed = discord.Embed(title="📈 NEPSE Index", color=color)
            embed.add_field(name="Current Index", value=f"**{index_val}**", inline=True)
            embed.add_field(name="Point Change", value=f"`{change_val}`", inline=True)
            embed.set_footer(text="Destiny Analytics • Live NEPSE Data")
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send("❌ Could not fetch NEPSE Index at this time.")

    @app_commands.command(name="stock", description="Check live or last closing price")
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        
        sym = symbol.upper()
        market = self.get_247_data()
        
        if sym in market:
            s = market[sym]
            color = 0x2ecc71 if float(s['chg']) > 0 else 0xe74c3c
            pressure = "🔥 Buying" if float(s['chg']) > 0 else "❄️ Selling"
            
            embed = discord.Embed(title=f"📊 {sym} | Destiny V2", color=color)
            embed.add_field(name="LTP (Last Price)", value=f"**Rs. {s['ltp']}**", inline=True)
            embed.add_field(name="Change", value=f"`{s['chg']}`", inline=True)
            embed.add_field(name="Volume", value=f"{s['vol']}", inline=True)
            embed.add_field(name="Sentiment", value=pressure, inline=False)
            embed.set_footer(text="Destiny Analytics • 24/7 Data")
            
            view = MarketButtons(sym)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"❌ **{sym}** not found. Check the symbol.")

async def setup(bot):
    await bot.add_cog(Market(bot))
