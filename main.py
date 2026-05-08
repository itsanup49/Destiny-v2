import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class DestinyBot(commands.Bot):
    def __init__(self):
        # Intents allow the bot to read messages and see members
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Automatically loads every .py file in your cogs folder
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded Cog: {filename}')
                except Exception as e:
                    print(f'❌ Error loading {filename}: {e}')

bot = DestinyBot()

@bot.command()
async def sync(ctx):
    """Force Discord to update slash commands. Type !sync in chat."""
    try:
        # This clears old commands (/stonk) and adds new ones (/stock)
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Destiny V2: Synced {len(synced)} commands. Restart your Discord app to see changes!")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user.name} is online. Type !sync to refresh commands.')

bot.run(os.getenv('DISCORD_TOKEN'))
