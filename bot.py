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
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"⚠️ <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=15)
    async def alert_engine(self):
        if not self.active_alerts: return
        try:
            live_data = await self.nepse.getLiveMarket()
            if not live_data: return
            # Correcting keys based on the API structure
            live_map = {item['symbol']: float(item.get('lastTradedPrice', 0)) for item in live_data}

            for user_id, config in list(self.active_alerts.items()):
                sym = config['symbol']
                if sym in live_map and live_map[sym] > 0:
                    current_p = live_map[sym]
                    if current_p <= config['low']:
                        msg = f"PRICE DROPPED! {sym} is at Rs. {current_p}"
                        del self.active_alerts[user_id] 
                        await self.fire_pings(user_id, config['channel'], msg, 5)
                    elif current_p >= config['high']:
                        msg = f"BREAKOUT! {sym} is at Rs. {current_p}"
                        del self.active_alerts[user_id]
                        await self.fire_pings(user_id, config['channel'], msg, 7)
        except: pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP and Market Info")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        # Fetching Live Market data
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None)
        
        if not stock:
            # Fallback for when market is closed
            list_data = await bot.nepse.getCompanyList()
            stock = next((s for s in list_data if s['symbol'] == sym), None)

        if stock:
            # Standardizing keys to avoid N/A or 0
            ltp = stock.get('lastTradedPrice') or stock.get('ltp') or 0
            change = stock.get('pointChange') or stock.get('change') or 0
            vol = stock.get('totalTradedQuantity') or stock.get('volume') or 0
            
            # Simple Pressure Logic based on Price Change since Depth is broken
            pressure = "🟢 Buying" if float(change) > 0 else "🔴 Selling" if float(change) < 0 else "⚖️ Neutral"
            color = 0x2ecc71 if float(change) > 0 else 0xe74c3c if float(change) < 0 else 0x34495e

            embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
            embed.add_field(name="Current Price", value=f"**Rs. {ltp}**", inline=True)
            embed.add_field(name="Change", value=f"{change}", inline=True)
            embed.add_field(name="Volume", value=f"{vol:,} units", inline=False)
            embed.add_field(name="Pressure (Est.)", value=pressure, inline=False)
            embed.set_footer(text="Data: Unofficial NEPSE API")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Could not find {sym}.")
    except Exception as e:
        await interaction.followup.send(f"⚠️ API Error: {e}")

@bot.tree.command(name="set_alert", description="Set high/low targets for burst pings")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {
        "symbol": sym, "low": low, "high": high, "channel": interaction.channel_id
    }
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**!")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
