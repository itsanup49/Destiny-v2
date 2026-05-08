import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_alerts = {} 
        self.check_alerts.start()

    def cog_unload(self):
        self.check_alerts.cancel()

    def get_price(self, symbol):
        """Uses the 24/7 data scraper for alerts"""
        try:
            url = "https://www.sharesansar.com/today-price"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 10 and cols[1].text.strip() == symbol:
                        return float(cols[6].text.strip().replace(',', ''))
            return None
        except: return None

    @tasks.loop(minutes=3)
    async def check_alerts(self):
        if not self.active_alerts: return

        for user_id, alerts in list(self.active_alerts.items()):
            for data in alerts[:]: # Iterate over a copy
                current_price = self.get_price(data['symbol'])
                
                if current_price:
                    triggered = False
                    reason = ""
                    
                    # Check Upper Limit
                    if data['upper'] and current_price >= data['upper']:
                        triggered = True
                        reason = f"🚀 Went ABOVE Rs. {data['upper']}"
                    
                    # Check Lower Limit
                    elif data['lower'] and current_price <= data['lower']:
                        triggered = True
                        reason = f"📉 Dropped BELOW Rs. {data['lower']}"
                        
                    if triggered:
                        user = await self.bot.fetch_user(user_id)
                        if user:
                            embed = discord.Embed(title="🚨 DESTINY PRICE ALERT", color=0xF1C40F)
                            embed.add_field(name="Symbol", value=f"**{data['symbol']}**", inline=True)
                            embed.add_field(name="Current Price", value=f"**Rs. {current_price}**", inline=True)
                            embed.add_field(name="Trigger", value=reason, inline=False)
                            await user.send(embed=embed)
                        
                        # Remove the specific alert after firing
                        self.active_alerts[user_id].remove(data)

    @app_commands.command(name="alert", description="Set upper and/or lower price limits")
    async def alert(self, interaction: discord.Interaction, symbol: str, upper_limit: float = None, lower_limit: float = None):
        await interaction.response.defer(ephemeral=True)
        
        sym = symbol.upper()
        
        if upper_limit is None and lower_limit is None:
            return await interaction.followup.send("❌ You must provide at least an `upper_limit` or a `lower_limit`.")

        if interaction.user.id not in self.active_alerts:
            self.active_alerts[interaction.user.id] = []
            
        self.active_alerts[interaction.user.id].append({
            "symbol": sym,
            "upper": upper_limit,
            "lower": lower_limit
        })
        
        msg = f"✅ Alert set for **{sym}**!\n"
        if upper_limit: msg += f"📈 Will DM if price hits **Rs. {upper_limit}** or higher.\n"
        if lower_limit: msg += f"📉 Will DM if price drops to **Rs. {lower_limit}** or lower."
        
        await interaction.followup.send(msg)

async def setup(bot):
    await bot.add_cog(Alerts(bot))
