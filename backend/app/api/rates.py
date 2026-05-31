import httpx
from fastapi import APIRouter

router = APIRouter()

BRECHA_API = "https://www.brecha-cambiaria.com/api/prices"

_CACHE = {"data": None, "ts": 0}


def get_rate_vars() -> dict:
    now = __import__("time").time()
    if now - _CACHE["ts"] < 30 and _CACHE["data"]:
        return _CACHE["data"]
    try:
        r = httpx.get(BRECHA_API, timeout=10)
        data = r.json()
        bcv_usd = data.get("bcv_usd", 0)
        usdt_avg = data.get("usdt_avg", 0)
        brecha_monto = round(usdt_avg - bcv_usd, 2)
        brecha_pct = round(((usdt_avg - bcv_usd) / bcv_usd * 100), 2) if bcv_usd else 0
        vars = {
            "bcv_usd": f"{bcv_usd:.2f}",
            "bcv_eur": f"{data.get('bcv_eur', 0):.2f}",
            "usdt_avg": f"{usdt_avg:.2f}",
            "brecha": f"{brecha_monto:.2f}",
            "brecha_pct": f"{brecha_pct:.1f}%",
        }
        _CACHE["data"] = vars
        _CACHE["ts"] = now
        return vars
    except Exception:
        return _CACHE["data"] or {}


@router.get("")
def get_rates():
    try:
        r = httpx.get(BRECHA_API, timeout=10)
        data = r.json()
        bcv_usd = data.get("bcv_usd", 0)
        usdt_avg = data.get("usdt_avg", 0)
        brecha_monto = usdt_avg - bcv_usd
        brecha_pct = round(((usdt_avg - bcv_usd) / bcv_usd * 100), 2) if bcv_usd else 0
        return {
            "bcv_usd": bcv_usd,
            "bcv_eur": data.get("bcv_eur", 0),
            "usdt_avg": usdt_avg,
            "brecha_monto": round(brecha_monto, 2),
            "brecha_pct": brecha_pct,
            "timestamp": data.get("timestamp", ""),
        }
    except Exception as e:
        return {"error": str(e)}
