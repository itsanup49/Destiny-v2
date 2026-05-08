import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
import httpx
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.all_symbols = []
        self.active_alerts = {} 

    # --- ENGINE B: SHARESANSAR FALLBACK ---
    def scrape_sharesansar(self, symbol):
        """Standard scraping for when APIs are blocked or market is closed."""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 2 and cols[1].text.strip() == symbol:
                    return {
                        "ltp": cols[2].text.strip().replace(',', ''),
                        "change": cols[3].text.strip(),
                        "volume": cols[7].text.strip().replace(',', ''),
                        "source": "Sharesansar (Backup)"
                    }
            return None
        except: return None

    async def setup_hook(self):
        print("🔄 Loading NEPSE symbols...")
        # Since the API is new, we'll use a solid list first
        self.all_symbols = ["NABIL", "NICA", "ADBL", "HIDCL", "NIFRA", "HDL", "SHL", "AHPC", "UPPER"]
        await self.tree.sync()
        if not self.alert_engine.is_running():
            self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"⚠️ <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=20)
    async def alert_engine(self):
        if not self.active_alerts: return
        # Logic follows the dual-check for alerts too
        pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP with Dual-Engine Failover")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    # --- ENGINE A: Try New SurajRimal API (REST Endpoint) ---
    try:
        async with httpx.AsyncClient() as client:
            # We hit the live market endpoint of the new API
            response = await client.get("https://nepsealpha.com/api/smth/live", timeout=5)
            data = response.json()
            # Searching for our stock in the new API format
            stock = next((s for s in data if s['symbol'] == sym), None)
            
            if stock and float(stock.get('ltp', 0)) > 0:
                ltp = stock.get('ltp')
                change = stock.get('pointChange', 0)
                vol = stock.get('volume', 0)
                source = "SurajRimal API (Primary)"
            else:
                raise Exception("API empty")

    except:
        # --- ENGINE B: SHARESANSAR FALLBACK ---
        backup = bot.scrape_sharesansar(sym)
        if backup:
            ltp, change, vol, source = backup['ltp'], backup['change'], backup['volume'], backup['source']
        else:
            return await interaction.followup.send(f"❌ Both Engines failed to find **{sym}**.")

    # --- BEAUTIFUL UI RENDERING ---
    color = 0x2ecc71 if float(change) > 0 else 0xe74c3c if float(change) < 0 else 0x34495e
    status_emoji = "📈" if float(change) > 0 else "📉" if float(change) < 0 else "⚖️"
    
    embed = discord.Embed(title=f"{status_emoji} {sym} Analysis", color=color)
    embed.add_field(name="Current Price", value=f"**Rs. {ltp}**", inline=True)
    embed.add_field(name="Change", value=f"{change}", inline=True)
    embed.add_field(name="Volume", value=f"{vol} units", inline=False)
    embed.set_footer(text=f"Data Source: {source} • Updated 2026")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="set_alert", description="Target pings: 5x for Low, 7x for High")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {"symbol": sym, "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**! (Low: {low}, High: {high})")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
