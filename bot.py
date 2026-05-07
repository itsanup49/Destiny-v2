import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
from dotenv import load_dotenv
from thefuzz import process
from nepse_api import Nepse 



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)
        self.live_tracking = {}
        self.all_symbols = []
        self.api = Nepse() # New initialization

    async def setup_hook(self):
        print("🔄 Fetching latest NEPSE symbols...")
        try:
            # The new library gets symbols very fast
            data = await self.api.get_price()
            self.all_symbols = [stock['symbol'] for stock in data]
            print(f"✅ Loaded {len(self.all_symbols)} symbols!")
        except Exception as e:
            print(f"⚠️ Initial fetch failed: {e}")
            self.all_symbols = ["NABIL", "NICA", "ADBL", "NIFRA", "UPPER"]
        
        await self.tree.sync()
        if not self.market_check_loop.is_running():
            self.market_check_loop.start()

    @tasks.loop(seconds=60) # Increased to 60s to avoid being blocked
    async def market_check_loop(self):
        if not self.live_tracking: return
        try:
            prices = await self.api.get_price()
            price_dict = {stock['symbol']: stock['ltp'] for stock in prices}
            
            for symbol, channel_id in self.live_tracking.items():
                if symbol in price_dict:
                    chan = self.get_channel(channel_id)
                    if chan: await chan.send(f"🕒 **Update:** {symbol} is Rs. {price_dict[symbol]}")
        except: pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live stock price")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        # api-nepse returns a list, we filter for our symbol
        prices = await bot.api.get_price()
        stock = next((s for s in prices if s['symbol'] == sym), None)
        
        if stock:
            embed = discord.Embed(title=f"📊 {sym}", color=discord.Color.blue())
            embed.add_field(name="LTP", value=f"**Rs. {stock['ltp']}**", inline=True)
            embed.add_field(name="Change", value=f"{stock['point_change']} ({stock['percentage_change']}%)", inline=True)
            embed.add_field(name="High/Low", value=f"H: {stock['high']} | L: {stock['low']}", inline=False)
            embed.set_footer(text="Powered by api-nepse")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Symbol **{sym}** not found.")
    except Exception as e:
        await interaction.followup.send("❌ NEPSE API is currently unreachable. Try again in a minute.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current: return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 35]

@bot.tree.command(name="track", description="Track stock price updates")
async def track(interaction: discord.Interaction, symbol: str):
    sym = symbol.strip().upper()
    bot.live_tracking[sym] = interaction.channel_id
    await interaction.response.send_message(f"📡 Now tracking **{sym}** every 60s.")

@bot.tree.command(name="stop", description="Stop all tracking")
async def stop(interaction: discord.Interaction):
    bot.live_tracking.clear()
    await interaction.response.send_message("🛑 Tracking stopped.")

@bot.event
async def on_ready():
    print(f'🚀 Destiny-v2 is live with api-nepse!')

bot.run(TOKEN)
