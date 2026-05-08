
import discord
from discord.ext import commands, tasks
import asyncio

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_alerts = {} # Format: {user_id: {"symbol": "NABIL", "target": 600}}

    @tasks.loop(minutes=1)
    async def check_alerts(self):
        # Logic to check prices every minute and ping users
        pass

async def setup(bot):
    await bot.add_cog(Alerts(bot))
