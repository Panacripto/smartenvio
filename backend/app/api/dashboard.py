from fastapi import APIRouter
from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query_one
import httpx
from app.config import settings

router = APIRouter()

def _try_q(sql: str, default=0):
    try:
        r = query_one(sql)
        return r["total"] if r else default
    except:
        return default

@router.get("/resumen")
def get_dashboard_resumen():
    try:
        clientes = odbc_connector.query("SELECT COUNT(*) as total FROM Sclientes")
    except:
        clientes = []
    try:
        inventario = odbc_connector.query("SELECT COUNT(*) as total FROM Sinventario")
    except:
        inventario = []
    try:
        cxc = odbc_connector.query("SELECT COUNT(*) as total FROM Scuentasxcobrar")
    except:
        cxc = []
    try:
        cxp = odbc_connector.query("SELECT COUNT(*) as total FROM Scuentasxpagar")
    except:
        cxp = []

    wa_phone = None
    wa_connected = False
    try:
        r = httpx.get(f"{settings.whatsapp_service_url}/api/status", timeout=3)
        if r.status_code == 200:
            d = r.json()
            wa_connected = d.get("status") == "connected"
            wa_phone = d.get("phone") if wa_connected else None
    except:
        pass

    return {
        "total_clientes": clientes[0]["total"] if clientes else 0,
        "total_inventario": inventario[0]["total"] if inventario else 0,
        "total_cxc": cxc[0]["total"] if cxc else 0,
        "total_cxp": cxp[0]["total"] if cxp else 0,
        "whatsapp_connected": wa_connected,
        "whatsapp_phone": wa_phone,
        "campanas_activas": _try_q("SELECT COUNT(*) as total FROM campaigns WHERE activo=1"),
        "ejecuciones_totales": _try_q("SELECT COUNT(*) as total FROM campaign_log"),
        "enviados_hoy": _try_q("SELECT COALESCE(SUM(enviados),0) as total FROM campaign_log WHERE date(ejecutado_en)=date('now','localtime')"),
        "fallidos_hoy": _try_q("SELECT COALESCE(SUM(fallidos),0) as total FROM campaign_log WHERE date(ejecutado_en)=date('now','localtime')"),
        "total_contactos": _try_q("SELECT COUNT(*) as total FROM contactos"),
    }
