import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
from dotenv import load_dotenv
from thefuzz import process
from nepse import Client

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)
        self.price_alerts = self.load_data()
        self.live_tracking = {}
        self.all_symbols = []
        self.nepse = Client()

    def load_data(self):
        if os.path.exists('data.json'):
            try:
                with open('data.json', 'r') as f: return json.load(f)
            except: return {}
        return {}

    def save_data(self):
        with open('data.json', 'w') as f:
            json.dump(self.price_alerts, f, indent=4)

    async def setup_hook(self):
        print("🔄 Fetching NEPSE symbols...")
        for attempt in range(3):
            try:
                securities = await self.nepse.security_client.get_securities()
                self.all_symbols = [s.symbol for s in securities]
                if self.all_symbols:
                    print(f"✅ Successfully loaded {len(self.all_symbols)} symbols!")
                    break
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(3)
        
        if not self.all_symbols:
            self.all_symbols = ["NABIL", "NICA", "ADBL", "UPPER", "HIDCL", "NIFRA"]
            
        await self.tree.sync()
        if not self.market_check_loop.is_running():
            self.market_check_loop.start()

    @tasks.loop(seconds=30)
    async def market_check_loop(self):
        monitored = set(self.price_alerts.keys()) | set(self.live_tracking.keys())
        for symbol in monitored:
            try:
                data = await self.nepse.security_client.get_company(symbol=symbol.upper())
                price = float(data.last_traded_price)
                if symbol in self.live_tracking:
                    chan = self.get_channel(self.live_tracking[symbol])
                    if chan: await chan.send(f"🕒 **Update:** {symbol} is Rs. {price}")
            except: continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live stock price")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    try:
        # We use a direct fetch here to bypass the list cache
        data = await bot.nepse.security_client.get_company(symbol=sym)
        embed = discord.Embed(title=f"📊 {sym}", color=0x2f3136)
        embed.add_field(name="Current Price (LTP)", value=f"**Rs. {data.last_traded_price}**", inline=False)
        embed.add_field(name="High/Low", value=f"H: {data.high_price} | L: {data.low_price}", inline=True)
        embed.set_footer(text="Destiny V2 • NEPSE Live Data")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send(f"❌ API Error: Could not get data for **{sym}**. The NEPSE server might be busy.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current: return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 35]

@bot.tree.command(name="track", description="Track stock every 30s")
async def track(interaction: discord.Interaction, symbol: str):
    bot.live_tracking[symbol.upper()] = interaction.channel_id
    await interaction.response.send_message(f"📡 Tracking {symbol.upper()} started.")

@bot.tree.command(name="stop", description="Stop all tracking")
async def stop(interaction: discord.Interaction):
    bot.live_tracking.clear()
    await interaction.response.send_message("🛑 All tracking stopped.")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live and synced!')

bot.run(TOKEN)
