import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

# --- BRANDING CONFIG ---
BOT_NAME = "Destiny NEPSE"
FOOTER_TEXT = "Destiny Analytics | Grade 12 Project"
COLOR_SUCCESS = 0x2ecc71
COLOR_DANGER = 0xe74c3c
COLOR_NEUTRAL = 0x34495e

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.all_symbols = []
        self.active_alerts = {}

    def fetch_market_data(self):
        """Unified scraper for live trading data."""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            data = {}
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) > 7:
                        sym = cols[1].text.strip()
                        data[sym] = {
                            "ltp": cols[2].text.strip().replace(',', ''),
                            "change": cols[3].text.strip(),
                            "vol": cols[7].text.strip().replace(',', '')
                        }
            return data
        except: return {}

    def fetch_broker_ranks(self):
        """Unified scraper for top 3 buying brokers."""
        try:
            url = "https://www.sharesansar.com/top-brokers"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            ranks = []
            if table:
                for i, row in enumerate(table.find_all('tr')[1:4], 1):
                    cols = row.find_all('td')
                    if len(cols) > 3:
                        name = cols[2].text.strip().split(' ')[0]
                        amt = cols[3].text.strip()
                        ranks.append(f"**{i}. {name}** — Rs. {amt}")
            return "\n".join(ranks) if ranks else "No trades detected yet."
        except: return "Broker data offline."

    async def setup_hook(self):
        print(f"🚀 {BOT_NAME} is initiating systems...")
        data = self.fetch_market_data()
        self.all_symbols = sorted(list(data.keys())) if data else ["NABIL", "NICA", "ADBL"]
        await self.tree.sync()
        self.alert_loop.start()

    @tasks.loop(seconds=30)
    async def alert_loop(self):
        if not self.active_alerts: return
        live_data = self.fetch_market_data()
        for uid, cfg in list(self.active_alerts.items()):
            sym = cfg['symbol']
            if sym in live_data:
                try:
                    price = float(live_data[sym]['ltp'])
                    if price <= cfg['low'] or price >= cfg['high']:
                        chan = self.get_channel(cfg['channel'])
                        if chan:
                            pings = 7 if price >= cfg['high'] else 5
                            for _ in range(pings):
                                await chan.send(f"🚨 <@{uid}> **{sym}** TARGET HIT: **Rs. {price}**")
                                await asyncio.sleep(2)
                        del self.active_alerts[uid]
                except: continue

bot = DestinyBot()

@bot.tree.command(name="stonk", description="View stock details, volume, and broker ranks")
async def stonk(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    market = bot.fetch_market_data()
    
    if sym in market:
        stock = market[sym]
        brokers = bot.fetch_broker_ranks()
        change_f = float(stock['change'].replace('+', ''))
        
        # UI Polish
        color = COLOR_SUCCESS if change_f > 0 else COLOR_DANGER if change_f < 0 else COLOR_NEUTRAL
        emoji = "🔼" if change_f > 0 else "🔽" if change_f < 0 else "⏺️"
        pressure = "🔥 HIGH BUYING" if change_f > 0 else "❄️ SELLING" if change_f < 0 else "NEUTRAL"

        embed = discord.Embed(title=f"{emoji} {sym} | {BOT_NAME}", color=color)
        embed.add_field(name="LTP (Current)", value=f"**Rs. {stock['ltp']}**", inline=True)
        embed.add_field(name="Change", value=f"`{stock['change']}`", inline=True)
        embed.add_field(name="Volume", value=f"`{stock['vol']} Units`", inline=True)
        embed.add_field(name="Market Pressure", value=f"**{pressure}**", inline=False)
        embed.add_field(name="🏆 Top 3 Buying Brokers (Today)", value=brokers, inline=False)
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ **{sym}** not found. Market is likely closed.")

@bot.tree.command(name="sync", description="Manually refresh market symbol list")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer()
    data = bot.fetch_market_data()
    if data:
        bot.all_symbols = sorted(list(data.keys()))
        await interaction.followup.send(f"✅ {BOT_NAME} database synced! {len(bot.all_symbols)} stocks ready.")
    else:
        await interaction.followup.send("⚠️ Market table empty. Search will update at 10:30 AM.")

@stonk.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)

