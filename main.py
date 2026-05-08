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
        # Load Cogs and print any errors if they fail
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded {filename}')
                except Exception as e:
                    print(f'❌ Failed to load {filename}: {e}')

bot = DestinyBot()

@bot.command()
async def sync(ctx):
    """Unlocked Sync Command - Anyone can run this now to fix slash commands"""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Destiny V2 Synced {len(synced)} commands to Discord!")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user.name} is ONLINE. Type !sync in chat.')

bot.run(os.getenv('DISCORD_TOKEN'))
