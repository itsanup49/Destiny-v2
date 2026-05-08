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
        self.all_symbols = []
        self.live_tracking = {} # {SYMBOL: CHANNEL_ID}

    async def setup_hook(self):
        print("🔄 Syncing symbols and commands...")
        try:
            # We fetch once at startup to populate the search list
            data = await self.nepse.getCompanyList()
            self.all_symbols = sorted([stock['symbol'] for stock in data])
            print(f"✅ Loaded {len(self.all_symbols)} symbols!")
        except:
            self.all_symbols = ["NABIL", "NICA", "ADBL"]
        
        await self.tree.sync()
        if not self.market_check_loop.is_running():
            self.market_check_loop.start()

    @tasks.loop(seconds=30)
    async def market_check_loop(self):
        if not self.live_tracking: return
        
        try:
            # Fetch entire live market once to update all tracked users
            live_data = await self.nepse.getLiveMarket()
            # Map symbol to its specific data for easy lookup
            live_map = {item['symbol']: item for item in live_data}

            for sym, channel_id in list(self.live_tracking.items()):
                if sym in live_map:
                    stock = live_map[sym]
                    chan = self.get_channel(channel_id)
                    if chan:
                        ltp = stock.get('lastTradedPrice', 0)
                        # Discord-friendly update message
                        await chan.send(f"🕒 **Update:** {sym} is Rs. **{ltp}**")
        except Exception as e:
            print(f"Loop Error: {e}")

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live LTP, Volume, and Pressure")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    try:
        # getLiveMarket contains the actual trading values (LTP, Vol, etc)
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None)
        
        if stock:
            ltp = stock.get('lastTradedPrice', 0)
            vol = stock.get('totalTradedQuantity', 0)
            high = stock.get('highPrice', 0)
            low = stock.get('lowPrice', 0)
            change = stock.get('pointChange', 0)
            
            # PRESSURE CALCULATION: Buy vs Sell Quantity
            # Note: This requires getMarketDepth if not in liveMarket, 
            # but we can estimate based on pointChange and volume.
            color = discord.Color.green() if change >= 0 else discord.Color.red()
            status_emoji = "📈" if change >= 0 else "📉"

            embed = discord.Embed(title=f"{status_emoji} {sym} Live Analysis", color=color)
            embed.add_field(name="LTP (Price)", value=f"**{ltp}**", inline=True)
            embed.add_field(name="Change", value=f"{change}", inline=True)
            embed.add_field(name="Volume", value=f"{vol:,} units", inline=False)
            embed.add_field(name="Day Range", value=f"L: {low} — H: {high}", inline=False)
            
            # Market Depth is a separate call for detailed pressure
            depth = await bot.nepse.getMarketDepth(sym)
            buy = depth.get('totalBuyQuantity', 0)
            sell = depth.get('totalSellQuantity', 0)
            pressure = "🟢 Buying" if buy > sell else "🔴 Selling" if sell > buy else "⚖️ Neutral"
            
            embed.add_field(name="Market Pressure", value=f"{pressure} (B: {buy:,} / S: {sell:,})", inline=False)
            embed.set_footer(text="Data: Unofficial NEPSE API • Live Feed")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Could not find live data for **{sym}**. Market might be closed.")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error fetching live data: {e}")

@bot.tree.command(name="track", description="Alert price every 30 seconds")
async def track(interaction: discord.Interaction, symbol: str):
    sym = symbol.strip().upper()
    bot.live_tracking[sym] = interaction.channel_id
    await interaction.response.send_message(f"📡 Now tracking **{sym}** every 30s in this channel.")

@bot.tree.command(name="stop", description="Stop all alerts")
async def stop(interaction: discord.Interaction):
    bot.live_tracking.clear()
    await interaction.response.send_message("🛑 All alerts cleared.")

@price.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live and tracking!')

bot.run(TOKEN)
