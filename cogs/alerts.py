import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Format: {user_id: {"symbol": "NICA", "target": 800, "type": "above"}}
        self.active_alerts = {} 
        self.check_alerts.start() # Start the background engine

    def cog_unload(self):
        self.check_alerts.cancel()

    def get_price(self, symbol):
        try:
            url = "https://www.sharesansar.com/live-trading"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 2 and cols[1].text.strip() == symbol:
                        return float(cols[2].text.strip().replace(',', ''))
            return None
        except: return None

    @tasks.loop(minutes=2)
    async def check_alerts(self):
        """Background loop that checks prices every 2 minutes."""
        if not self.active_alerts:
            return

        for user_id, data in list(self.active_alerts.items()):
            current_price = self.get_price(data['symbol'])
            
            if current_price:
                target = data['target']
                symbol = data['symbol']
                
                # Check if target hit
                if (data['type'] == "above" and current_price >= target) or \
                   (data['type'] == "below" and current_price <= target):
                    
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        embed = discord.Embed(title="🚨 DESTINY PRICE ALERT", color=0xF1C40F)
                        embed.add_field(name="Symbol", value=symbol, inline=True)
                        embed.add_field(name="Target Hit", value=f"Rs. {current_price}", inline=True)
                        embed.set_footer(text="Destiny Analytics • Alert System")
                        
                        await user.send(embed=embed)
                        # Remove alert after firing to save memory
                        del self.active_alerts[user_id]

    @app_commands.command(name="setalert", description="Get a DM when a stock hits your price")
    async def setalert(self, interaction: discord.Interaction, symbol: str, price: float, direction: str):
        """direction: type 'above' or 'below'"""
        await interaction.response.defer(ephemeral=True)
        
        sym = symbol.upper()
        dir_type = direction.lower()
        
        if dir_type not in ["above", "below"]:
            return await interaction.followup.send("❌ Use 'above' or 'below' for direction.")

        self.active_alerts[interaction.user.id] = {
            "symbol": sym,
            "target": price,
            "type": dir_type
        }
        
        await interaction.followup.send(f"✅ Alert set! I'll DM you when **{sym}** goes **{dir_type}** Rs. {price}.")

async def setup(bot):
    await bot.add_cog(Alerts(bot))
