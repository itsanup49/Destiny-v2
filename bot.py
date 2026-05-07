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
        super().__init__(command_prefix="!", intents=intents)
        self.price_alerts = self.load_data()
        self.live_tracking = {}
        self.all_symbols = []
        # Initialize client but don't start it yet
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
        # Fetch symbols safely
        try:
            securities = await self.nepse.security_client.get_securities()
            self.all_symbols = [s.symbol for s in securities]
            print(f"✅ Loaded {len(self.all_symbols)} NEPSE symbols!")
        except Exception as e:
            print(f"⚠️ API Fetch Error: {e}")
            self.all_symbols = ["NABIL", "ADBL", "NICA", "NIFRA", "UPPER"]

        await self.tree.sync()
        if not self.market_check_loop.is_running():
            self.market_check_loop.start()

    @tasks.loop(seconds=30)
    async def market_check_loop(self):
        monitored = set(self.price_alerts.keys()) | set(self.live_tracking.keys())
        if not monitored: return

        for symbol in monitored:
            try:
                # Use the correct security_client method
                data = await self.nepse.security_client.get_company(symbol=symbol.upper())
                price = float(data.last_traded_price)

                if symbol in self.live_tracking:
                    chan = self.get_channel(self.live_tracking[symbol])
                    if chan: await chan.send(f"🕒 **Update:** {symbol} is Rs. {price}")

                if symbol in self.price_alerts:
                    a = self.price_alerts[symbol]
                    if price >= a['max'] or price <= a['low']:
                        chan = self.get_channel(a['channel'])
                        status = "🚀 MAX" if price >= a['max'] else "📉 LOW"
                        if chan: await chan.send(f"🔔 **{status} ALERT:** {symbol} hit {price}!")
                        del self.price_alerts[symbol]
                        self.save_data()
            except:
                continue

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live stock price")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    try:
        data = await bot.nepse.security_client.get_company(symbol=symbol.upper())
        embed = discord.Embed(title=f"📊 {symbol.upper()}", color=discord.Color.green())
        embed.add_field(name="LTP", value=f"Rs. {data.last_traded_price}")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Symbol not found or API error.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

# (Include stop, track, set_alert commands here similar to above)

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live!')

bot.run(TOKEN)
