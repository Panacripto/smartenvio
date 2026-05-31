from fastapi import APIRouter
from pydantic import BaseModel
from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query_one, execute as sqlite_execute

router = APIRouter()

DEFAULT_MENSAJE = "Hola *{FC_DESCRIPCION}*, su apreciada cuenta presenta  *{FC_DOCUMENTOS}* facturas *{FC_CRITERIO}* que totalizan un monto de *{FC_SALDO_TOTAL} $*. Agradecemos realizar el pago a la mayor brevedad posible, si ya realizo su pago, haga caso omiso a este mensaje, Gracias."


def _load_config():
    row = query_one("SELECT mensaje FROM config_cobranza WHERE id=1")
    return {"mensaje": row["mensaje"] if row else DEFAULT_MENSAJE}


def _save_config(data: dict):
    sqlite_execute("UPDATE config_cobranza SET mensaje=?", (data.get("mensaje", ""),))


class CobranzaConfig(BaseModel):
    mensaje: str


@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config")
def set_config(body: CobranzaConfig):
    _save_config(body.model_dump())
    return {"ok": True}


@router.get("")
def listar_cobranza(search: str = "", criterio: str = "ambas"):
    texto_criterio = "PENDIENTES"
    sql = """
        SELECT c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO,
               COALESCE(SUM(x.FCC_SALDOMONEDAEXT), 0) as FC_SALDO_TOTAL,
               COUNT(*) as FC_DOCUMENTOS
        FROM Sclientes c
        INNER JOIN Scuentasxcobrar x ON c.FC_CODIGO = x.FCC_CODIGO
        WHERE x.FCC_SALDOMONEDAEXT > 0
          AND c.FC_TELEFONO IS NOT NULL
          AND c.FC_TELEFONO <> ''
    """
    if criterio == "vencidas":
        sql += " AND x.FCC_FECHAVENCIMIENTO < CURRENT_DATE"
        texto_criterio = "VENCIDAS"
    elif criterio == "por_vencer":
        sql += " AND x.FCC_FECHAVENCIMIENTO >= CURRENT_DATE"
        texto_criterio = "POR VENCER"
    if search:
        escaped = search.replace("'", "''").upper()
        sql += " AND (UPPER(c.FC_CODIGO) LIKE '%{}%' OR UPPER(c.FC_DESCRIPCION) LIKE '%{}%' OR UPPER(c.FC_TELEFONO) LIKE '%{}%')".format(
            escaped, escaped, escaped
        )
    sql += " GROUP BY c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO"
    sql += " ORDER BY FC_SALDO_TOTAL DESC"
    rows = odbc_connector.query(sql)
    for row in rows:
        row["FC_CRITERIO"] = texto_criterio
    return rows


@router.get("/detalle/{codigo}")
def detalle_cliente(codigo: str):
    sql = """
        SELECT FCC_NUMERO, FCC_FECHAVENCIMIENTO, FCC_MONTODOCUMENTO,
               FCC_SALDOMONEDAEXT, FCC_DESCRIPCIONMOV
        FROM Scuentasxcobrar
        WHERE FCC_CODIGO = ? AND FCC_SALDOMONEDAEXT > 0
        ORDER BY FCC_FECHAVENCIMIENTO
    """
    return odbc_connector.query(sql, [codigo])
