
import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
from thefuzz import process

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.symbols = []

    def scrape_live(self):
        url = "https://www.sharesansar.com/live-trading"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', {'id': 'headertall'})
        data = {}
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) > 7:
                    sym = cols[1].text.strip()
                    data[sym] = {"ltp": cols[2].text.strip(), "change": cols[3].text.strip(), "vol": cols[7].text.strip()}
        return data

    @app_commands.command(name="stonk", description="Check LTP and Market Sentiment")
    async def stonk(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        market = self.scrape_live()
        sym = symbol.upper()
        if sym in market:
            s = market[sym]
            color = 0x2ecc71 if "+" in s['change'] else 0xe74c3c
            embed = discord.Embed(title=f"📊 {sym} | Destiny NEPSE", color=color)
            embed.add_field(name="LTP", value=f"Rs. {s['ltp']}", inline=True)
            embed.add_field(name="Change", value=s['change'], inline=True)
            embed.add_field(name="Pressure", value="🔥 Buying" if "+" in s['change'] else "❄️ Selling", inline=False)
            embed.set_footer(text="Destiny Analytics")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Symbol not found or market closed.")

async def setup(bot):
    await bot.add_cog(Market(bot))
