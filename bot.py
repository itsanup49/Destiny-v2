import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            # This line now skips utils.py so it doesn't crash
            if filename.endswith('.py') and filename != 'utils.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded: {filename}')
                except Exception as e:
                    print(f'❌ Cog Error {filename}: {e}')

bot = DestinyBot()

@bot.event
async def on_ready():
    print(f"--- DESTINY V2 ONLINE AS {bot.user} ---")

@bot.command()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ synced {len(synced)} commands! RESTART your Discord app now.")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
