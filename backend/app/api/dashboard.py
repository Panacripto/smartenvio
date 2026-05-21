from fastapi import APIRouter
from app.database.odbc_connector import odbc_connector

router = APIRouter()

@router.get("/resumen")
def get_dashboard_resumen():
    clientes = odbc_connector.query("SELECT COUNT(*) as total FROM Sclientes")
    inventario = odbc_connector.query("SELECT COUNT(*) as total FROM Sinventario")
    cxc = odbc_connector.query("SELECT COUNT(*) as total FROM Scuentasxcobrar")
    cxp = odbc_connector.query("SELECT COUNT(*) as total FROM Scuentasxpagar")

    return {
        "total_clientes": clientes[0]["total"] if clientes else 0,
        "total_inventario": inventario[0]["total"] if inventario else 0,
        "total_cxc": cxc[0]["total"] if cxc else 0,
        "total_cxp": cxp[0]["total"] if cxp else 0,
    }
