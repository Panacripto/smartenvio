import json, os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from app.config import settings
from app.database.odbc_connector import odbc_connector

router = APIRouter()

def _load_empresa_config():
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "facturadigital_config.json")
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except:
        return {}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "smartenvio_config.json")

DEFAULT_REGLAS = [
    {"dias": 15, "activo": True, "etiqueta": "Vence en 15 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, le recordamos que su(s) factura(s) vence(n) en *15 d\u00edas*. Son *{FC_DOCUMENTOS}* documento(s) por un total de *{FC_SALDO_TOTAL} $. Agradecemos realizar el pago a la brevedad. Gracias."},
    {"dias": 7, "activo": True, "etiqueta": "Vence en 7 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, su(s) factura(s) vence(n) en *7 d\u00edas* - *{FC_DOCUMENTOS}* documento(s) por *{FC_SALDO_TOTAL} $. Por favor realice el pago. Gracias."},
    {"dias": 3, "activo": True, "etiqueta": "Vence en 3 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, su(s) factura(s) vence(n) en *3 d\u00edas* - *{FC_DOCUMENTOS}* documento(s) por *{FC_SALDO_TOTAL} $. No deje vencer su factura. Gracias."},
    {"dias": 0, "activo": True, "etiqueta": "Vence hoy", "mensaje": "Hola *{FC_DESCRIPCION}*, su apreciada cuenta presenta *{FC_DOCUMENTOS}* facturas *{FC_CRITERIO}* que totalizan un monto de *{FC_SALDO_TOTAL} $. Agradecemos realizar el pago a la mayor brevedad posible, si ya realizo su pago, haga caso omiso a este mensaje, Gracias."},
]

class ReglaConfig(BaseModel):
    dias: int
    activo: bool = True
    etiqueta: str = ""
    mensaje: str = ""

class SmartEnviosConfigBody(BaseModel):
    activo: bool = True
    reglas: list[ReglaConfig] = []

class EnviarRequest(BaseModel):
    dias: int
    mensaje: str = ""


def _load_config() -> dict:
    default = {"activo": True, "reglas": DEFAULT_REGLAS}
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            merged_reglas = []
            saved = {r["dias"]: r for r in cfg.get("reglas", [])}
            for d in DEFAULT_REGLAS:
                sr = saved.get(d["dias"], {})
                merged_reglas.append({**d, **sr})
            return {"activo": cfg.get("activo", True), "reglas": merged_reglas}
    except:
        return default


def _save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _query_regla(dias: int) -> list[dict]:
    if dias == 0:
        date_expr = "CURRENT_DATE"
        criterio = "VENCE HOY"
    else:
        date_expr = f"CURRENT_DATE + {dias}"
        criterio = f"VENCE EN {dias} D\u00cdAS"

    sql = f"""
        SELECT c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO,
               COALESCE(SUM(x.FCC_SALDOMONEDAEXT), 0) as FC_SALDO_TOTAL,
               COUNT(*) as FC_DOCUMENTOS
        FROM Sclientes c
        INNER JOIN Scuentasxcobrar x ON c.FC_CODIGO = x.FCC_CODIGO
        WHERE x.FCC_SALDOMONEDAEXT > 0
          AND c.FC_TELEFONO IS NOT NULL
          AND c.FC_TELEFONO <> ''
          AND x.FCC_FECHAVENCIMIENTO = {date_expr}
        GROUP BY c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO
        ORDER BY FC_SALDO_TOTAL DESC
    """
    rows = odbc_connector.query(sql)
    for r in rows:
        r["FC_CRITERIO"] = criterio
    return rows


@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config")
def set_config(body: SmartEnviosConfigBody):
    cfg = {
        "activo": body.activo,
        "reglas": [r.model_dump() for r in body.reglas],
    }
    _save_config(cfg)
    return cfg


@router.get("/clientes")
def listar_clientes_por_regla():
    cfg = _load_config()
    if not cfg["activo"]:
        return {"reglas": []}
    result = []
    for r in cfg["reglas"]:
        if not r["activo"]:
            continue
        clientes = _query_regla(r["dias"])
        if clientes:
            result.append({
                "dias": r["dias"],
                "etiqueta": r["etiqueta"],
                "mensaje": r["mensaje"],
                "clientes": clientes,
            })
    return {"reglas": result}


@router.post("/enviar")
def enviar_smartenvio(body: EnviarRequest):
    cfg = _load_config()
    if not cfg["activo"]:
        raise HTTPException(400, "SmartEnvios est\u00e1 desactivado")

    regla = next((r for r in cfg["reglas"] if r["dias"] == body.dias), None)
    if not regla:
        raise HTTPException(400, f"No se encontr\u00f3 regla para {body.dias} d\u00edas")
    if not regla["activo"]:
        raise HTTPException(400, f"La regla de {body.dias} d\u00edas est\u00e1 desactivada")

    clientes = _query_regla(body.dias)
    if not clientes:
        raise HTTPException(400, "No hay clientes para esta regla")

    template = body.mensaje or regla["mensaje"]
    enviados = 0
    fallidos = 0
    detalles = []

    empresa_cfg = _load_empresa_config()
    for c in clientes:
        tel = str(c.get("FC_TELEFONO", "")).replace(" ", "")
        if not tel:
            fallidos += 1
            detalles.append(f"\u2717 {c['FC_DESCRIPCION']} - sin tel\u00e9fono")
            continue
        msg = template
        msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", ""))
        msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", ""))
        for key in ("FC_CODIGO", "FC_DESCRIPCION", "FC_TELEFONO"):
            msg = msg.replace("{" + key + "}", str(c.get(key, "")))
        msg = msg.replace("{FC_SALDO_TOTAL}", f"{c.get('FC_SALDO_TOTAL', 0):.2f}")
        msg = msg.replace("{FC_DOCUMENTOS}", str(c.get("FC_DOCUMENTOS", "")))
        msg = msg.replace("{FC_CRITERIO}", c.get("FC_CRITERIO", ""))

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{settings.whatsapp_service_url}/api/send",
                    json={"telefono": tel, "mensaje": msg},
                )
                if resp.status_code >= 400:
                    fallidos += 1
                    detalles.append(f"\u2717 {c['FC_DESCRIPCION']}: error WhatsApp")
                else:
                    enviados += 1
                    detalles.append(f"\u2713 {c['FC_DESCRIPCION']}")
        except httpx.ConnectError:
            fallidos += 1
            detalles.append(f"\u2717 {c['FC_DESCRIPCION']}: servicio WhatsApp no disponible")
        except Exception as e:
            fallidos += 1
            detalles.append(f"\u2717 {c['FC_DESCRIPCION']}: {str(e)[:50]}")

    return {"enviados": enviados, "fallidos": fallidos, "detalles": detalles}
