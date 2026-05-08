import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from nepse import AsyncNepse # Correct import for basic-bgnr library
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.nepse = AsyncNepse()
        self.nepse.setTLSVerification(False) # Needed due to NEPSE's SSL issues
        self.all_symbols = []

    async def setup_hook(self):
        print("🔄 Loading symbols from Unofficial API...")
        try:
            # This fetches the list which usually contains the latest LTP
            data = await self.nepse.getCompanyList()
            self.all_symbols = [stock['symbol'] for stock in data]
            print(f"✅ Loaded {len(self.all_symbols)} symbols!")
        except Exception as e:
            print(f"⚠️ Fetch failed: {e}")
            self.all_symbols = ["NABIL", "NICA", "ADBL", "NIFRA", "UPPER"]
        
        await self.tree.sync()

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP using Unofficial API")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    try:
        # We fetch the full list to get the most recent LTP even if market is closed
        data = await bot.nepse.getCompanyList()
        stock = next((s for s in data if s['symbol'] == sym), None)
        
        if stock:
            # The keys in this API are usually 'lastTradedPrice' or similar
            ltp = stock.get('lastTradedPrice', 'N/A')
            change = stock.get('change', '0.0')
            
            embed = discord.Embed(title=f"📊 {sym} (Last Traded)", color=discord.Color.blue())
            embed.add_field(name="LTP", value=f"Rs. {ltp}", inline=True)
            embed.add_field(name="Symbol", value=stock.get('symbol'), inline=True)
            embed.set_footer(text="Data: NepseUnofficialApi")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Symbol {sym} not found in current list.")
    except Exception as e:
        await interaction.followup.send("⚠️ API Error: Unable to fetch data. NEPSE might be blocking requests.")

@price.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=5)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches]

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is using the Unofficial NEPSE API!')

bot.run(TOKEN)
