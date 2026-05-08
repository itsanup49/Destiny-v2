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
        # This acts as a shortcut to the chart command
        await interaction.response.send_message(f"Generating trend for {self.symbol}... Use `/chart` for full view.", ephemeral=True)

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_live_data(self):
        try:
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
                        data[sym] = {"ltp": cols[2].text.strip(), "chg": cols[3].text.strip()}
            return data
        except: return {}

    @app_commands.command(name="stock", description="Live price, change, and buttons")
    async def stock(self, interaction: discord.Interaction, symbol: str):
        # FIX: Tells Discord to wait (Stops the "did not respond" error)
        await interaction.response.defer()
        
        sym = symbol.upper()
        market = self.get_live_data()
        
        if sym in market:
            s = market[sym]
            color = 0x2ecc71 if "+" in s['chg'] else 0xe74c3c
            embed = discord.Embed(title=f"📈 {sym} | Destiny V2", color=color)
            embed.add_field(name="Price", value=f"**Rs. {s['ltp']}**", inline=True)
            embed.add_field(name="Change", value=f"`{s['chg']}`", inline=True)
            embed.set_footer(text="Destiny Analytics • Live Data")
            
            view = MarketButtons(sym)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"❌ {sym} not found. Market is likely closed.")

async def setup(bot):
    await bot.add_cog(Market(bot))
