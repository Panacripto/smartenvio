from fastapi import APIRouter, HTTPException
from app.database.odbc_connector import odbc_connector

router = APIRouter()

@router.get("")
def listar_clientes(search: str = "", codigo_desde: str = "", codigo_hasta: str = "", solo_con_telefono: bool = False):
    sql = "SELECT * FROM Sclientes WHERE 1=1"
    if search:
        escaped = search.replace("'", "''").upper()
        sql += " AND (UPPER(FC_CODIGO) LIKE '%{}%' OR UPPER(FC_DESCRIPCION) LIKE '%{}%')".format(escaped, escaped)
    if codigo_desde:
        escaped = codigo_desde.replace("'", "''")
        sql += " AND FC_CODIGO >= '{}'".format(escaped)
    if codigo_hasta:
        escaped = codigo_hasta.replace("'", "''")
        sql += " AND FC_CODIGO <= '{}'".format(escaped)
    if solo_con_telefono:
        sql += " AND FC_TELEFONO IS NOT NULL AND FC_TELEFONO <> ''"
    sql += " ORDER BY FC_CODIGO"
    return odbc_connector.query(sql)

@router.get("/{codigo}")
def get_cliente(codigo: str):
    rows = odbc_connector.query("SELECT * FROM Sclientes WHERE FC_CODIGO = ?", [codigo])
    if not rows:
        raise HTTPException(404, "Cliente no encontrado")
    return rows[0]

@router.get("/telefono/{telefono}")
def buscar_por_telefono(telefono: str):
    escaped = telefono.replace("'", "''").upper()
    return odbc_connector.query("SELECT * FROM Sclientes WHERE UPPER(FC_TELEFONO) LIKE '%{}%'".format(escaped))
