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
        # Stores alert config: {USER_ID: {"symbol": SYM, "low": FLOAT, "high": FLOAT, "channel": ID}}
        self.active_alerts = {} 

    async def setup_hook(self):
        print("🔄 Loading NEPSE symbols...")
        try:
            data = await self.nepse.getCompanyList()
            self.all_symbols = sorted([stock['symbol'] for stock in data])
            print(f"✅ Loaded {len(self.all_symbols)} symbols!")
        except:
            self.all_symbols = ["NABIL", "NICA", "ADBL", "HIDCL"]
        
        await self.tree.sync()
        if not self.alert_engine.is_running():
            self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        """Sends the burst pings (3s intervals)"""
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"⚠️ <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=15) # Market check frequency
    async def alert_engine(self):
        if not self.active_alerts: return
        try:
            live_data = await self.nepse.getLiveMarket()
            if not live_data: return
            live_map = {item['symbol']: float(item['lastTradedPrice']) for item in live_data}

            for user_id, config in list(self.active_alerts.items()):
                sym = config['symbol']
                if sym in live_map:
                    current_p = live_map[sym]
                    
                    # 🔴 PRICE BELOW LIMIT
                    if current_p <= config['low']:
                        msg = f"PRICE DROPPED! {sym} is at Rs. {current_p} (Target: {config['low']})"
                        del self.active_alerts[user_id] 
                        await self.fire_pings(user_id, config['channel'], msg, 5)
                    
                    # 🟢 PRICE ABOVE LIMIT
                    elif current_p >= config['high']:
                        msg = f"BREAKOUT! {sym} is at Rs. {current_p} (Target: {config['high']})"
                        del self.active_alerts[user_id]
                        await self.fire_pings(user_id, config['channel'], msg, 7)
        except Exception as e:
            print(f"Alert Engine Error: {e}")

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live LTP and market pressure")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        # Check live first, then fallback to company list for closed market LTP
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None)
        status_label = "LIVE"
        
        if not stock:
            list_data = await bot.nepse.getCompanyList()
            stock = next((s for s in list_data if s['symbol'] == sym), None)
            status_label = "CLOSED"

        if stock:
            ltp = stock.get('lastTradedPrice') or stock.get('ltp') or 0
            change = stock.get('pointChange', 0)
            vol = stock.get('totalTradedQuantity') or stock.get('volume') or 0
            
            # Fetch Depth for Pressure
            depth = await bot.nepse.getMarketDepth(sym)
            buy = depth.get('totalBuyQuantity', 0)
            sell = depth.get('totalSellQuantity', 0)
            pressure = "🟢 Buying" if buy > sell else "🔴 Selling" if sell > buy else "⚖️ Neutral"

            embed = discord.Embed(title=f"📊 {sym} Analysis", color=0x2f3136)
            embed.add_field(name="Current Price", value=f"**Rs. {ltp}**", inline=True)
            embed.add_field(name="Change", value=str(change), inline=True)
            embed.add_field(name="Volume", value=f"{vol:,}", inline=False)
            embed.add_field(name="Pressure", value=f"{pressure} (B: {buy:,} / S: {sell:,})", inline=False)
            embed.set_footer(text=f"Market Status: {status_label}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Could not find data for {sym}.")
    except Exception as e:
        await interaction.followup.send(f"⚠️ API Error: {e}")

@bot.tree.command(name="set_alert", description="Set targets for burst pings")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {
        "symbol": sym,
        "low": low,
        "high": high,
        "channel": interaction.channel_id
    }
    await interaction.response.send_message(
        f"🎯 **Alert Armed for {sym}**\n"
        f"📉 Below {low}: 5 pings\n"
        f"📈 Above {high}: 7 pings\n"
        "Tracking starts now!"
    )

@bot.tree.command(name="sync_now", description="Force refresh commands")
async def sync_now(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message("✅ Commands synced globally!")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is operational and ready for trading!')

bot.run(TOKEN)
