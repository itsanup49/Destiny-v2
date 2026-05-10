import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import cogs.utils as utils_module
from cogs.utils import fetch_symbols_async

load_dotenv()

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load NEPSE symbols before cogs start
        print("⏳ Fetching NEPSE symbols...")
        utils_module.ALL_SYMBOLS = await fetch_symbols_async()
        print(f"✅ Loaded {len(utils_module.ALL_SYMBOLS)} symbols")

        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != 'utils.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded: {filename}')
                except Exception as e:
                    print(f'❌ Cog Error {filename}: {e}')

        # Auto-sync slash commands on startup
        await self.tree.sync()
        print("✅ Slash commands synced")

bot = DestinyBot()

@bot.event
async def on_ready():
    print(f"--- DESTINY V2 ONLINE AS {bot.user} ---")

@bot.command()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} commands! Restart Discord to see them.")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
