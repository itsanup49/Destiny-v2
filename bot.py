import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import asyncio
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG  –  edit these before running
# ─────────────────────────────────────────────
BOT_TOKEN      = "YOUR_DISCORD_BOT_TOKEN"   # from Discord Developer Portal
ALERT_CHANNEL  = 123456789012345678         # right-click your channel → Copy ID
ALERTS_FILE    = "alerts.json"
CHECK_INTERVAL = 1                          # minutes
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ── Helpers ───────────────────────────────────

def load_alerts() -> dict:
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE) as f:
            return json.load(f)
    return {}


def save_alerts(data: dict):
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def fetch_price(symbol: str) -> float | None:
    """Scrape live price from Merolagani."""
    url = f"https://merolagani.com/CompanyDetail.aspx?symbol={symbol.upper()}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")

        # Merolagani shows LTP in a span with this class
        ltp_tag = soup.find("span", {"id": lambda x: x and "ctl00_ContentPlaceHolder1_LiveTrading1_lblLTP" in str(x)})
        if not ltp_tag:
            # fallback: look for the price inside table rows
            for td in soup.find_all("td"):
                if "LTP" in td.get_text():
                    sibling = td.find_next_sibling("td")
                    if sibling:
                        val = sibling.get_text(strip=True).replace(",", "")
                        return float(val)
            return None

        val = ltp_tag.get_text(strip=True).replace(",", "")
        return float(val) if val else None
    except Exception:
        return None


def make_alert_embed(symbol: str, price: float, kind: str, threshold: float, user_id: int) -> discord.Embed:
    color = discord.Color.red() if kind == "low" else discord.Color.green()
    arrow = "🔴 DROPPED BELOW" if kind == "low" else "🟢 ROSE ABOVE"
    embed = discord.Embed(
        title=f"📊 NEPSE Alert – {symbol}",
        description=f"**{symbol}** {arrow} your threshold!",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Current Price", value=f"Rs. {price:,.2f}", inline=True)
    embed.add_field(name="Your Threshold", value=f"Rs. {threshold:,.2f}", inline=True)
    embed.add_field(name="Alert Type", value=kind.upper(), inline=True)
    embed.set_footer(text=f"User: <@{user_id}> • NEPSE Bot")
    return embed


# ── Background Task ───────────────────────────

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_prices():
    alerts = load_alerts()
    if not alerts:
        return

    channel = bot.get_channel(ALERT_CHANNEL)
    if not channel:
        print(f"[ERROR] Channel {ALERT_CHANNEL} not found.")
        return

    triggered_keys = []

    for key, info in alerts.items():
        symbol   = info["symbol"]
        high     = info.get("high")
        low      = info.get("low")
        user_id  = info["user_id"]

        price = await fetch_price(symbol)
        if price is None:
            print(f"[WARN] Could not fetch price for {symbol}")
            continue

        print(f"[INFO] {symbol} = Rs.{price}")

        if high is not None and price >= high:
            embed = make_alert_embed(symbol, price, "high", high, user_id)
            await channel.send(content=f"<@{user_id}>", embed=embed)
            triggered_keys.append(key)

        elif low is not None and price <= low:
            embed = make_alert_embed(symbol, price, "low", low, user_id)
            await channel.send(content=f"<@{user_id}>", embed=embed)
            triggered_keys.append(key)

    # Remove triggered alerts so they don't spam
    for k in triggered_keys:
        alerts.pop(k, None)
    if triggered_keys:
        save_alerts(alerts)


@check_prices.before_loop
async def before_check():
    await bot.wait_until_ready()


# ── Slash Commands ────────────────────────────

@tree.command(name="watch", description="Set a price alert for a NEPSE stock")
@app_commands.describe(
    symbol="Stock symbol (e.g. NABIL, NTC, UPPER)",
    high="Alert when price goes ABOVE this value (optional)",
    low="Alert when price goes BELOW this value (optional)"
)
async def watch(interaction: discord.Interaction, symbol: str, high: float = None, low: float = None):
    if high is None and low is None:
        await interaction.response.send_message("❌ Please provide at least a `high` or `low` value.", ephemeral=True)
        return

    symbol = symbol.upper()
    await interaction.response.defer(ephemeral=True)

    price = await fetch_price(symbol)
    if price is None:
        await interaction.followup.send(f"❌ Could not find **{symbol}** on Merolagani. Check the symbol and try again.", ephemeral=True)
        return

    alerts = load_alerts()
    key = f"{interaction.user.id}_{symbol}"
    alerts[key] = {
        "symbol":  symbol,
        "high":    high,
        "low":     low,
        "user_id": interaction.user.id,
        "set_at":  datetime.utcnow().isoformat()
    }
    save_alerts(alerts)

    parts = []
    if high: parts.append(f"🟢 High: Rs. {high:,.2f}")
    if low:  parts.append(f"🔴 Low:  Rs. {low:,.2f}")

    embed = discord.Embed(
        title=f"✅ Alert Set – {symbol}",
        description="\n".join(parts),
        color=discord.Color.blurple()
    )
    embed.add_field(name="Current Price", value=f"Rs. {price:,.2f}")
    embed.set_footer(text="I'll ping you in the alert channel when triggered!")
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="price", description="Check the current price of a NEPSE stock")
@app_commands.describe(symbol="Stock symbol (e.g. NABIL, NTC, UPPER)")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    symbol = symbol.upper()
    await interaction.response.defer()
    price = await fetch_price(symbol)
    if price is None:
        await interaction.followup.send(f"❌ Could not fetch price for **{symbol}**.")
        return
    embed = discord.Embed(
        title=f"📈 {symbol} – Current Price",
        description=f"**Rs. {price:,.2f}**",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="Source: Merolagani")
    await interaction.followup.send(embed=embed)


@tree.command(name="list", description="List all your active price alerts")
async def list_alerts(interaction: discord.Interaction):
    alerts = load_alerts()
    user_alerts = {k: v for k, v in alerts.items() if v["user_id"] == interaction.user.id}

    if not user_alerts:
        await interaction.response.send_message("📭 You have no active alerts.", ephemeral=True)
        return

    embed = discord.Embed(title="🔔 Your Active Alerts", color=discord.Color.blurple())
    for info in user_alerts.values():
        val = []
        if info.get("high"): val.append(f"High ↑ Rs. {info['high']:,.2f}")
        if info.get("low"):  val.append(f"Low ↓ Rs. {info['low']:,.2f}")
        embed.add_field(name=info["symbol"], value="\n".join(val), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="remove", description="Remove a price alert for a stock")
@app_commands.describe(symbol="Stock symbol to remove alert for")
async def remove_alert(interaction: discord.Interaction, symbol: str):
    symbol = symbol.upper()
    alerts = load_alerts()
    key = f"{interaction.user.id}_{symbol}"
    if key in alerts:
        del alerts[key]
        save_alerts(alerts)
        await interaction.response.send_message(f"🗑️ Alert for **{symbol}** removed.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No alert found for **{symbol}**.", ephemeral=True)


@tree.command(name="removeall", description="Remove ALL your active alerts")
async def remove_all(interaction: discord.Interaction):
    alerts = load_alerts()
    before = len(alerts)
    alerts = {k: v for k, v in alerts.items() if v["user_id"] != interaction.user.id}
    removed = before - len(alerts)
    save_alerts(alerts)
    await interaction.response.send_message(f"🗑️ Removed **{removed}** alert(s).", ephemeral=True)


# ── Bot Events ────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")
    check_prices.start()
    print(f"✅ Price checker started – every {CHECK_INTERVAL} min")


bot.run(BOT_TOKEN)
