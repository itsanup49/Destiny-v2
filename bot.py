import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from dotenv import load_dotenv
from thefuzz import process
try:
    from nepse import MarketClient
except ImportError:
    from nepse.core import MarketClient

# Initialize the Market Client instead
nepse_client = MarketClient()




load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
nepse_client = SecurityClient()

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.price_alerts = self.load_data()
        self.live_tracking = {}
        self.all_symbols = []

    def load_data(self):
        if os.path.exists('data.json'):
            try:
                with open('data.json', 'r') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_data(self):
        with open('data.json', 'w') as f:
            json.dump(self.price_alerts, f, indent=4)

    async def setup_hook(self):
        try:
            securities = await nepse_client.get_securities()
            self.all_symbols = [s.symbol for s in securities]
            print(f"✅ Loaded {len(self.all_symbols)} NEPSE symbols!")
        except Exception as e:
            self.all_symbols = ["NABIL", "ADBL", "NICA", "NIFRA", "UPPER"]
            print(f"⚠️ API Error: {e}. Using fallback symbols.")

        await self.tree.sync()
        self.market_check_loop.start()

    @tasks.loop(seconds=30)
    async def market_check_loop(self):
        monitored = set(self.price_alerts.keys()) | set(self.live_tracking.keys())
        if not monitored: return

        for symbol in monitored:
            try:
                data = await nepse_client.get_security_details(symbol)
                if not data: continue
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
            except: pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Check live stock price with search UI")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    data = await nepse_client.get_security_details(symbol.upper())
    if data:
        embed = discord.Embed(title=f"📊 {symbol.upper()}", color=discord.Color.blue())
        embed.add_field(name="LTP", value=f"Rs. {data.last_traded_price}")
        embed.set_footer(text="Destiny-v2 • NEPSE Live")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Symbol not found.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

@bot.tree.command(name="set_alert", description="Ping me when price hits X high or Y low")
async def set_alert(interaction: discord.Interaction, symbol: str, max_price: float, low_price: float):
    symbol = symbol.upper()
    bot.price_alerts[symbol] = {
        "user_id": interaction.user.id, "max": max_price, "low": low_price, "channel": interaction.channel_id
    }
    bot.save_data()
    await interaction.response.send_message(f"✅ Alert saved for **{symbol}**.")

@bot.tree.command(name="track", description="Get price updates every 30s in this channel")
async def track(interaction: discord.Interaction, symbol: str):
    bot.live_tracking[symbol.upper()] = interaction.channel_id
    await interaction.response.send_message(f"📡 Now tracking **{symbol.upper()}** every 30s.")

@bot.tree.command(name="stop", description="Stop all alerts and 30s tracking")
async def stop(interaction: discord.Interaction):
    bot.live_tracking.clear()
    bot.price_alerts.clear()
    bot.save_data()
    await interaction.response.send_message("🛑 Cleared all active tasks.")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live on Railway!')

bot.run(TOKEN)
