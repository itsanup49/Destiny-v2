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
        # Store alerts: {USER_ID: {"symbol": SYM, "low": FLOAT, "high": FLOAT, "channel": ID}}
        self.active_alerts = {} 

    async def setup_hook(self):
        try:
            data = await self.nepse.getCompanyList()
            self.all_symbols = sorted([stock['symbol'] for stock in data])
        except:
            self.all_symbols = ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
        self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        """Sends a burst of pings every 3 seconds"""
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"⚠️ <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=10) # Checks the market every 10s
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
                    
                    # 🔴 LOWER LIMIT HIT (Below)
                    if current_p <= config['low']:
                        msg = f"PRICE DROPPED! {sym} is at Rs. {current_p} (Target: {config['low']})"
                        del self.active_alerts[user_id] # Stop alert after firing
                        await self.fire_pings(user_id, config['channel'], msg, 5)
                    
                    # 🟢 UPPER LIMIT HIT (High)
                    elif current_p >= config['high']:
                        msg = f"PRICE BREAKOUT! {sym} is at Rs. {current_p} (Target: {config['high']})"
                        del self.active_alerts[user_id] # Stop alert after firing
                        await self.fire_pings(user_id, config['channel'], msg, 7)
        except:
            pass

bot = DestinyBot()

@bot.tree.command(name="set_alert", description="Set high/low targets for pings")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {
        "symbol": sym,
        "low": low,
        "high": high,
        "channel": interaction.channel_id
    }
    await interaction.response.send_message(
        f"🎯 **Alert Configured for {sym}**\n"
        f"📉 Below {low}: 5 Pings\n"
        f"📈 Above {high}: 7 Pings\n"
        "I'll watch the market for you!"
    )

@bot.tree.command(name="price", description="Check live stock data")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None)
        if stock:
            ltp = stock.get('lastTradedPrice', 0)
            change = stock.get('pointChange', 0)
            embed = discord.Embed(title=f"📊 {sym}", color=discord.Color.blue())
            embed.add_field(name="Price", value=f"**{ltp}**")
            embed.add_field(name="Change", value=str(change))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Market closed or symbol not found.")
    except:
        await interaction.followup.send("API Error.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=5)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches]

bot.run(TOKEN)
