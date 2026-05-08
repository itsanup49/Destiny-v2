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
        # Automatically load all files in the /cogs folder
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded Cog: {filename}')
                except Exception as e:
                    print(f'❌ Failed to load {filename}: {e}')
        await self.tree.sync()

bot = DestinyBot()

@bot.event
async def on_ready():
    print(f'🚀 {bot.user.name} is online and deployed!')

bot.run(os.getenv('DISCORD_TOKEN'))

