import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from nepse import AsyncNepse
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.nepse = AsyncNepse()
        self.nepse.setTLSVerification(False)
        self.all_symbols = [] # This will hold ALL listed stocks

    async def setup_hook(self):
        print("🔄 Loading ALL symbols from NEPSE...")
        try:
            # Fetch every single company on the market
            data = await self.nepse.getCompanyList()
            self.all_symbols = sorted([stock['symbol'] for stock in data])
            print(f"✅ Loaded {len(self.all_symbols)} symbols!")
        except Exception as e:
            print(f"⚠️ Fetch failed: {e}")
            self.all_symbols = ["NABIL", "NICA", "ADBL"]
        
        # This makes commands show up globally (can take 1 hour)
        await self.tree.sync()

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP, Volume, and Pressure")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    try:
        data = await bot.nepse.getCompanyList()
        stock = next((s for s in data if s['symbol'] == sym), None)
        
        if stock:
            # Pulling the correct fields from NepseUnofficialApi
            ltp = stock.get('lastTradedPrice', 0)
            vol = stock.get('totalTradedQuantity', 0)
            high = stock.get('highPrice', 0)
            low = stock.get('lowPrice', 0)
            
            # Buying/Selling Pressure (Market Depth) logic
            # These fields depend on NEPSE's live depth data
            buy_p = stock.get('totalBuyQuantity', 0)
            sell_p = stock.get('totalSellQuantity', 0)
            
            color = discord.Color.blue()
            pressure_text = "⚖️ Neutral"
            if buy_p > sell_p:
                pressure_text = f"🟢 Buying Pressure ({buy_p:,})"
                color = discord.Color.green()
            elif sell_p > buy_p:
                pressure_text = f"🔴 Selling Pressure ({sell_p:,})"
                color = discord.Color.red()

            embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
            embed.add_field(name="Current Price (LTP)", value=f"**Rs. {ltp}**", inline=False)
            embed.add_field(name="Volume", value=f"{vol:,} units", inline=True)
            embed.add_field(name="Pressure", value=pressure_text, inline=True)
            embed.add_field(name="Day Range", value=f"L: {low} — H: {high}", inline=False)
            embed.set_footer(text="Data: NepseUnofficialApi • Market Closed/Live")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Symbol {sym} not found.")
    except Exception as e:
        await interaction.followup.send("⚠️ API Error. NEPSE might be updating.")

# --- DYNAMIC SEARCH (FIXES YOUR SEARCH ISSUE) ---
@price.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    # Searches through ALL symbols loaded in setup_hook
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

# --- THE "FIX MISSING COMMANDS" COMMAND ---
@bot.command()
@commands.is_owner() # Only you can run this
async def sync_now(ctx):
    """Force commands to show up in the current server immediately"""
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("✅ Commands synced to THIS server. Try typing `/` now!")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is ready!')

bot.run(TOKEN)
