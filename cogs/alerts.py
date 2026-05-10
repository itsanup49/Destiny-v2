import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
from .utils import ALL_SYMBOLS, get_nepal_time

BASE_URL = "https://nepseapi.surajrimal.dev"

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_alerts = {}  # { user_id: [ {symbol, upper, lower, channel_id} ] }
        self.check_alerts.start()

    def cog_unload(self):
        self.check_alerts.cancel()

    async def get_price(self, symbol: str) -> float | None:
        """Async price fetch from NepseAPI LiveMarket."""
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}/LiveMarket") as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    for item in data:
                        if item.get("symbol", "").upper() == symbol.upper():
                            ltp = (
                                item.get("ltp") or
                                item.get("lastTradedPrice") or
                                item.get("close")
                            )
                            return float(str(ltp).replace(",", "")) if ltp else None
        except Exception:
            return None

    @tasks.loop(minutes=3)
    async def check_alerts(self):
        if not self.active_alerts:
            return

        # Cache the full LiveMarket once per loop instead of hitting API per user
        timeout = aiohttp.ClientTimeout(total=10)
        price_cache = {}
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}/LiveMarket") as resp:
                    if resp.status == 200:
                        market_data = await resp.json()
                        for item in market_data:
                            sym = item.get("symbol", "").upper()
                            ltp = (
                                item.get("ltp") or
                                item.get("lastTradedPrice") or
                                item.get("close")
                            )
                            if sym and ltp:
                                try:
                                    price_cache[sym] = float(str(ltp).replace(",", ""))
                                except ValueError:
                                    pass
        except Exception:
            return  # If API is down, skip this loop cycle silently

        for user_id, alerts in list(self.active_alerts.items()):
            for alert_data in alerts[:]:
                sym = alert_data["symbol"]
                current_price = price_cache.get(sym)
                if current_price is None:
                    continue

                triggered = False
                reason = ""

                if alert_data["upper"] and current_price >= alert_data["upper"]:
                    triggered = True
                    reason = f"🚀 Rose ABOVE Rs. **{alert_data['upper']:,.2f}**"
                elif alert_data["lower"] and current_price <= alert_data["lower"]:
                    triggered = True
                    reason = f"📉 Dropped BELOW Rs. **{alert_data['lower']:,.2f}**"

                if triggered:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="🚨 Price Alert Triggered!",
                                color=0xF1C40F,
                                timestamp=get_nepal_time()
                            )
                            embed.add_field(name="Symbol", value=f"
