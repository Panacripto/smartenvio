from fastapi import APIRouter
from app.database.odbc_connector import odbc_connector

router = APIRouter()

@router.get("/")
def listar_compras():
    return odbc_connector.query("SELECT * FROM SDetalleCompra")
