from fastapi import APIRouter
from datetime import datetime
from app.database.odbc_connector import odbc_connector

router = APIRouter()

@router.get("/cobrar")
def listar_cxc():
    return odbc_connector.query("SELECT * FROM Scuentasxcobrar")

@router.get("/pagar")
def listar_cxp():
    return odbc_connector.query("SELECT * FROM Scuentasxpagar")
