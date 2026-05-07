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
        try:
            securities = await self.nepse.security_client.get_securities()
            self.all_symbols = [s.symbol for s in securities]
            print(f"✅ Loaded {len(self.all_symbols)} NEPSE symbols!")
        except Exception as e:
            print(f"⚠️ API Fetch Error: {e}")
            self.all_symbols = ["NABIL", "ADBL", "NICA", "NIFRA", "UPPER"]
        
        # Syncing globally (can take 1 hour)
        await self.tree.sync()

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
                if symbol in self.price_alerts:
                    a = self.price_alerts[symbol]
                    if price >= a['max'] or price <= a['low']:
                        chan = self.get_channel(a['channel'])
                        status = "🚀 MAX" if price >= a['max'] else "📉 LOW"
                        if chan: await chan.send(f"🔔 **{status} ALERT:** {symbol} hit {price}!")
                        del self.price_alerts[symbol]
                        self.save_data()
            except: continue

bot = DestinyBot()

# --- COMMANDS ---

@bot.tree.command(name="price", description="Check live stock price")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    clean_symbol = symbol.strip().upper()
    try:
        data = await bot.nepse.security_client.get_company(symbol=clean_symbol)
        embed = discord.Embed(title=f"📊 {clean_symbol}", color=discord.Color.blue())
        embed.add_field(name="LTP", value=f"Rs. {data.last_traded_price}", inline=False)
        embed.set_footer(text="Destiny-v2 • NEPSE Live")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Could not find '{clean_symbol}'. Make sure it's a valid symbol.")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 40]

@bot.tree.command(name="track", description="Get price updates every 30 seconds")
async def track(interaction: discord.Interaction, symbol: str):
    sym = symbol.strip().upper()
    bot.live_tracking[sym] = interaction.channel_id
    if not bot.market_check_loop.is_running():
        bot.market_check_loop.start()
    await interaction.response.send_message(f"📡 Now tracking **{sym}** every 30s in this channel.")

@bot.tree.command(name="stop", description="Stop all tracking and alerts")
async def stop(interaction: discord.Interaction):
    bot.live_tracking.clear()
    bot.price_alerts.clear()
    bot.save_data()
    await interaction.response.send_message("🛑 All active tracking and alerts have been cleared.")

# --- ADMIN COMMAND (Instant Sync) ---
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ Commands forced to sync globally! Wait 5 mins.")

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is live!')

bot.run(TOKEN)
