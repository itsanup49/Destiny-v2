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
        # Automatically loads everything in the cogs folder
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        await self.tree.sync()

bot = DestinyBot()

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Run !sync in Discord to update /commands list"""
    await bot.tree.sync()
    await ctx.send("✅ Destiny V2 commands synced to Discord servers!")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user.name} Deployed. Use !sync to refresh slash commands.')

bot.run(os.getenv('DISCORD_TOKEN'))
