
import discord
from discord.ext import commands
from discord import app_commands
import requests, io, matplotlib.pyplot as plt
from bs4 import BeautifulSoup

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ipo", description="Check current IPOs")
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
        
        embed = discord.Embed(title="🚀 Active IPOs", description="\n".join(issues) if issues else "None found", color=0x5865F2)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="broker", description="Top 3 Buying Brokers")
    async def broker(self, interaction: discord.Interaction):
        await interaction.response.defer()
        res = requests.get("https://www.sharesansar.com/top-brokers", headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        ranking = []
        rows = soup.find_all('tr')[1:4]
        for i, r in enumerate(rows, 1):
            c = r.find_all('td')
            if len(c) > 3: ranking.append(f"**{i}. {c[2].text.strip().split()[0]}** — Rs. {c[3].text.strip()}")
        
        embed = discord.Embed(title="🏆 Top Buyers Today", description="\n".join(ranking), color=0xF1C40F)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Tools(bot))
