import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')

bot = DestinyBot()

@bot.command()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} commands. RESTART YOUR DISCORD APP NOW.")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
