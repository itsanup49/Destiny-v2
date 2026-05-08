import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.all_symbols = []
        self.active_alerts = {} 

    def fetch_nepse_table(self):
        """Scrapes the live market table from Sharesansar."""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            
            data_map = {}
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 7:
                        sym = cols[1].text.strip()
                        data_map[sym] = {
                            "ltp": cols[2].text.strip().replace(',', ''),
                            "change": cols[3].text.strip(),
                            "vol": cols[7].text.strip().replace(',', '')
                        }
            return data_map
        except Exception as e:
            print(f"Scraper Error: {e}")
            return {}

    async def setup_hook(self):
        """Runs when the bot starts up."""
        print("🔄 Bot is starting... trying to load symbols.")
        data = self.fetch_nepse_table()
        if data:
            self.all_symbols = sorted(list(data.keys()))
            print(f"✅ Loaded {len(self.all_symbols)} symbols.")
        else:
            print("⚠️ Table was empty on startup. Use /sync_symbols later.")
            self.all_symbols = ["NABIL", "NICA", "ADBL", "HIDCL"]
            
        await self.tree.sync()
        if not self.alert_engine.is_running():
            self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        """Sends multiple pings for alerts."""
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"🚨 <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=30)
    async def alert_engine(self):
        """Checks targets against live data every 30 seconds."""
        if not self.active_alerts: return
        live_data = self.fetch_nepse_table()
        
        for user_id, config in list(self.active_alerts.items()):
            sym = config['symbol']
            if sym in live_data:
                try:
                    price = float(live_data[sym]['ltp'])
                    if price <= config['low']:
                        await self.fire_pings(user_id, config['channel'], f"LOW TARGET! {sym} is at Rs. {price}", 5)
                        del self.active_alerts[user_id]
                    elif price >= config['high']:
                        await self.fire_pings(user_id, config['channel'], f"HIGH TARGET! {sym} is at Rs. {price}", 7)
                        del self.active_alerts[user_id]
                except: continue

# Create Bot instance
bot = DestinyBot()

@bot.tree.command(name="price", description="Check live NEPSE price from Sharesansar")
@app_commands.describe(symbol="The stock symbol (e.g., NABIL)")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.fetch_nepse_table()
    
    if sym in data:
        stock = data[sym]
        change_val = stock['change']
        # Set color: Green for profit, Red for loss
        color = 0x2ecc71 if "+" in change_val else 0xe74c3c if "-" in change_val else 0x34495e
        
        embed = discord.Embed(title=f"📊 {sym} Live Data", color=color)
        embed.add_field(name="Current Price", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Point Change", value=f"{change_val}", inline=True)
        embed.add_field(name="Traded Volume", value=f"{stock['vol']} units", inline=False)
        embed.set_footer(text="Source: Sharesansar Live Table • 2026")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Market data for **{sym}** is currently unavailable. Market opens at 11:00 AM NST.")

@bot.tree.command(name="set_alert", description="Burst pings: 5x for Low, 7x for High")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {
        "symbol": sym, 
        "low": low, 
        "high": high, 
        "channel": interaction.channel_id
    }
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**! Watching the live table...")

@bot.tree.command(name="sync_symbols", description="Manually refresh the stock symbol list")
async def sync_symbols(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.fetch_nepse_table()
    if data:
        bot.all_symbols = sorted(list(data.keys()))
        await interaction.followup.send(f"✅ Synced {len(bot.all_symbols)} stocks! Search should work now.")
    else:
        await interaction.followup.send("⚠️ Table is empty. Try again during market hours (10:30 AM - 3:00 PM).")

@price.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not bot.all_symbols: return []
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

# Run the bot
bot.run(TOKEN)
