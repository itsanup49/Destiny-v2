import discord
from discord.ext import commands
from discord import app_commands
import requests, io, matplotlib.pyplot as plt
from bs4 import BeautifulSoup

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="chart", description="Visual trend for a symbol")
    async def chart(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()
        
        # Chart Design
        plt.style.use('dark_background')
        plt.figure(figsize=(8, 4))
        plt.plot([1, 2, 3, 4, 5], [100, 105, 102, 110, 108], color='#5865F2', linewidth=2, marker='o')
        plt.title(f"{sym} Trend Analysis | Destiny")
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        file = discord.File(buf, filename="chart.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="ipo", description="Check open investment issues")
    async def ipo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        res = requests.get("https://www.sharesansar.com/existing-issues", headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        issues = []
        table = soup.find('table')
        if table:
            for row in table.find_all('tr')[1:6]:
                cols = row.find_all('td')
                if len(cols) > 2: issues.append(f"📌 **{cols[2].text.strip()}**")
        
        embed = discord.Embed(title="🚀 Open IPOs / Right Shares", description="\n".join(issues) or "No active issues.", color=0x5865F2)
        embed.set_footer(text="Destiny Analytics")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Tools(bot))
