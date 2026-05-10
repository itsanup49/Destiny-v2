import aiohttp
from datetime import datetime
import pytz

# ── Nepal Time ────────────────────────────────────────────────────────────────

def get_nepal_time() -> datetime:
    """Returns current Nepal time as a datetime object (for Discord embed timestamps)."""
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    return datetime.now(nepal_tz)

def get_market_status() -> tuple[str, str]:
    """Returns (time_string, status_emoji_string) — use this for display text."""
    now = get_nepal_time()
    # Market open: Sun–Thu, 11:00–15:00 NPT
    is_open = (now.weekday() in (6, 0, 1, 2, 3)) and (11 <= now.hour < 15)
    time_str = now.strftime("%I:%M %p")
    status   = "🟢 OPEN" if is_open else "🔴 CLOSED"
    return time_str, status

# ── Symbol List ───────────────────────────────────────────────────────────────

FALLBACK_SYMBOLS = sorted([
    "NABIL", "NICA", "HDL", "NYADI", "AHPC", "SHL", "UPPER", "GBIME", "CIT",
    "HIDCL", "NTC", "NBL", "ADBL", "SANIMA", "PCBL", "PRVU", "HRL", "NRIC",
    "API", "AKPL", "UPW", "LEC", "MEN", "NIFRA", "MLBSL", "NICL", "NLIC",
    "SICL", "EBL", "MNHL", "CHCL", "NHPC", "RIDI", "KKHC", "SHPC", "BPCL",
    "MEGA", "SCB", "KBL", "LBBL", "MBL", "SHINE", "JBBL", "CORBL", "CZBIL",
    "SBI", "NIB", "NIMB", "SRBL", "SAPDBL",
])

async def fetch_symbols_async() -> list[str]:
    """Async symbol fetch from NepseAPI — call this once on bot startup."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://nepseapi.surajrimal.dev/CompanyList") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    symbols = []
                    for item in data:
                        sym = (
                            item.get("symbol") or
                            item.get("Symbol") or
                            item.get("stockSymbol")
                        )
                        if sym:
                            symbols.append(sym.strip().upper())
                    if len(symbols) > 10:
                        return sorted(list(set(symbols)))
    except Exception:
        pass
    return FALLBACK_SYMBOLS

# Starts as fallback — bot.py will replace this on startup
ALL_SYMBOLS = FALLBACK_SYMBOLS
