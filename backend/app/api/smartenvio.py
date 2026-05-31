from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from datetime import date
from app.config import settings
from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query as sqlite_query, query_one, execute as sqlite_execute

router = APIRouter()

DEFAULT_REGLAS = [
    {"dias": 15, "activo": True, "etiqueta": "Vence en 15 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, le recordamos que su(s) factura(s) vence(n) en *15 d\u00edas*. Son *{FC_DOCUMENTOS}* documento(s) por un total de *{FC_SALDO_TOTAL} $. Agradecemos realizar el pago a la brevedad. Gracias."},
    {"dias": 7, "activo": True, "etiqueta": "Vence en 7 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, su(s) factura(s) vence(n) en *7 d\u00edas* - *{FC_DOCUMENTOS}* documento(s) por *{FC_SALDO_TOTAL} $. Por favor realice el pago. Gracias."},
    {"dias": 3, "activo": True, "etiqueta": "Vence en 3 d\u00edas", "mensaje": "Hola *{FC_DESCRIPCION}*, su(s) factura(s) vence(n) en *3 d\u00edas* - *{FC_DOCUMENTOS}* documento(s) por *{FC_SALDO_TOTAL} $. No deje vencer su factura. Gracias."},
    {"dias": 0, "activo": True, "etiqueta": "Vence hoy", "mensaje": "Hola *{FC_DESCRIPCION}*, su apreciada cuenta presenta *{FC_DOCUMENTOS}* facturas *{FC_CRITERIO}* que totalizan un monto de *{FC_SALDO_TOTAL} $. Agradecemos realizar el pago a la mayor brevedad posible, si ya realizo su pago, haga caso omiso a este mensaje, Gracias."},
    {"dias": -1, "activo": True, "etiqueta": "Vencidas", "mensaje": "Hola *{FC_DESCRIPCION}*, su apreciada cuenta presenta *{FC_DOCUMENTOS}* facturas *{FC_CRITERIO}* que totalizan un monto de *{FC_SALDO_TOTAL} $. Agradecemos realizar el pago a la mayor brevedad posible, si ya realizo su pago, haga caso omiso a este mensaje, Gracias."},
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
    row = query_one("SELECT activo FROM config_smartenvio WHERE id=1")
    activo = bool(row["activo"]) if row else True
    reglas_db = sqlite_query("SELECT * FROM config_smartenvio_reglas ORDER BY dias DESC")
    reglas = []
    for d in DEFAULT_REGLAS:
        rd = next((r for r in reglas_db if r["dias"] == d["dias"]), None)
        if rd:
            reglas.append({
                "dias": rd["dias"],
                "activo": bool(rd["activo"]),
                "etiqueta": rd["etiqueta"],
                "mensaje": rd["mensaje"],
            })
        else:
            reglas.append(dict(d))
    return {"activo": activo, "reglas": reglas}


def _save_config(cfg: dict):
    sqlite_execute("UPDATE config_smartenvio SET activo=?", (1 if cfg.get("activo") else 0,))
    for r in cfg.get("reglas", []):
        existing = query_one("SELECT id FROM config_smartenvio_reglas WHERE dias=?", (r["dias"],))
        if existing:
            sqlite_execute("UPDATE config_smartenvio_reglas SET activo=?, etiqueta=?, mensaje=? WHERE dias=?",
                          (1 if r.get("activo") else 0, r.get("etiqueta", ""), r.get("mensaje", ""), r["dias"]))
        else:
            sqlite_execute("INSERT INTO config_smartenvio_reglas (dias, activo, etiqueta, mensaje) VALUES (?,?,?,?)",
                          (r["dias"], 1 if r.get("activo") else 0, r.get("etiqueta", ""), r.get("mensaje", "")))


def _query_regla(dias: int) -> list[dict]:
    if dias < 0:
        date_expr = "CURRENT_DATE"
        op = "<"
        criterio = "VENCIDAS"
    elif dias == 0:
        date_expr = "CURRENT_DATE"
        op = "="
        criterio = "VENCE HOY"
    else:
        date_expr = f"CURRENT_DATE + {dias}"
        op = "="
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
          AND x.FCC_FECHAVENCIMIENTO {op} {date_expr}
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

    empresa_cfg = {}
    try:
        from app.api.facturadigital import _load_config as _load_fd
        empresa_cfg = _load_fd()
    except:
        pass

    for c in clientes:
        tel = str(c.get("FC_TELEFONO", "")).replace(" ", "")
        if not tel:
            fallidos += 1
            detalles.append(f"\u2717 {c['FC_DESCRIPCION']} - sin tel\u00e9fono")
            continue
        msg = template
        msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", ""))
        msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", ""))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            msg = msg.replace("{" + k + "}", v)
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


def _leer_pagos_sqlite() -> list[dict]:
    return sqlite_query("""
        SELECT p.codigo, p.nombre,
               d.numero, d.monto, d.fecha_vencimiento,
               CAST(JULIANDAY('now') - JULIANDAY(d.fecha_vencimiento) AS INTEGER) AS dias
        FROM pagos_proveedores p
        INNER JOIN pagos_documentos d ON d.proveedor_codigo = p.codigo
        ORDER BY p.nombre, d.fecha_vencimiento
    """)


def _agrupar_proveedores_smartenvio(rows: list) -> list[dict]:
    grupos = {}
    for r in rows:
        cod = r["codigo"]
        if cod not in grupos:
            grupos[cod] = {"codigo": cod, "nombre": r.get("nombre") or cod, "total": 0.0, "documentos": 0}
        grupos[cod]["total"] += float(r.get("monto") or 0)
        grupos[cod]["documentos"] += 1
    return list(grupos.values())


@router.get("/proveedores")
def listar_proveedores_pago():
    cfg = query_one("SELECT activo, mensaje, telefono1, telefono2, telefono3 FROM config_gestionpagos WHERE id=1")
    if not cfg or not cfg.get("activo"):
        return {"activo": False, "reglas": []}

    rows = _leer_pagos_sqlite()
    if not rows:
        return {"activo": True, "reglas": []}

    vencidas = [r for r in rows if int(r.get("dias") or 0) > 0]
    por_vencer = [r for r in rows if int(r.get("dias") or 0) <= 0]

    reglas = []
    if vencidas:
        agrupados = _agrupar_proveedores_smartenvio(vencidas)
        reglas.append({
            "tipo": "vencidas",
            "etiqueta": "Pagos vencidos",
            "mensaje": cfg["mensaje"],
            "proveedores": agrupados,
            "total_general": round(sum(p["total"] for p in agrupados), 2),
        })
    if por_vencer:
        agrupados = _agrupar_proveedores_smartenvio(por_vencer)
        reglas.append({
            "tipo": "por_vencer",
            "etiqueta": "Pagos por vencer",
            "mensaje": cfg["mensaje"],
            "proveedores": agrupados,
            "total_general": round(sum(p["total"] for p in agrupados), 2),
        })

    telefonos = []
    for k in ("telefono1", "telefono2", "telefono3"):
        t = (cfg.get(k) or "").strip()
        if t:
            telefonos.append(t)

    return {"activo": True, "reglas": reglas, "telefonos": telefonos}


def _enviar_regla_interna(dias: int, mensaje: str = "") -> dict:
    cfg = _load_config()
    regla = next((r for r in cfg["reglas"] if r["dias"] == dias), None)
    if not regla or not regla["activo"]:
        return {"enviados": 0, "fallidos": 0, "detalles": [f"Regla {dias}d inactiva"]}
    clientes = _query_regla(dias)
    if not clientes:
        return {"enviados": 0, "fallidos": 0, "detalles": [f"Sin clientes para {dias}d"]}
    template = mensaje or regla["mensaje"]
    env, fal, dets = 0, 0, []
    empresa_cfg = {}
    try:
        from app.api.facturadigital import _load_config as _load_fd
        empresa_cfg = _load_fd()
    except:
        pass
    for c in clientes:
        tel = str(c.get("FC_TELEFONO", "")).replace(" ", "")
        if not tel:
            fal += 1
            dets.append(f"\u2717 {c['FC_DESCRIPCION']} - sin tel\u00e9fono")
            continue
        msg = template
        msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", ""))
        msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", ""))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            msg = msg.replace("{" + k + "}", v)
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
                    fal += 1
                    dets.append(f"\u2717 {c['FC_DESCRIPCION']}: error WhatsApp")
                else:
                    env += 1
                    dets.append(f"\u2713 {c['FC_DESCRIPCION']}")
        except httpx.ConnectError:
            fal += 1
            dets.append(f"\u2717 {c['FC_DESCRIPCION']}: servicio WhatsApp no disponible")
        except Exception as e:
            fal += 1
            dets.append(f"\u2717 {c['FC_DESCRIPCION']}: {str(e)[:50]}")
    return {"enviados": env, "fallidos": fal, "detalles": dets}


@router.post("/enviar-todo")
def enviar_todo():
    resultados = {}
    total_env, total_fal = 0, 0
    detalles_totales = []

    cfg_cobranza = _load_config()
    if cfg_cobranza["activo"]:
        for r in cfg_cobranza["reglas"]:
            if not r["activo"]:
                continue
            res = _enviar_regla_interna(r["dias"])
            resultados[r["etiqueta"]] = res
            total_env += res["enviados"]
            total_fal += res["fallidos"]
            detalles_totales.append(f"{r['etiqueta']}: {res['enviados']} enviados, {res['fallidos']} fallidos")

    from app.api.gestionpagos import enviar_gestion_pagos
    for criterio in ("vencidas", "por_vencer"):
        try:
            res = enviar_gestion_pagos(criterio=criterio, incluir_pdf=True)
            etiqueta = "Pagos vencidos" if criterio == "vencidas" else "Pagos por vencer"
            resultados[etiqueta] = res
            total_env += res["enviados"]
            total_fal += res["fallidos"]
            detalles_totales.append(f"{etiqueta}: {res['enviados']} enviados, {res['fallidos']} fallidos")
        except HTTPException as e:
            resultados[criterio] = {"enviados": 0, "fallidos": 0, "detalles": [str(e.detail)]}
            detalles_totales.append(f"{criterio}: {e.detail}")
        except Exception as e:
            resultados[criterio] = {"enviados": 0, "fallidos": 0, "detalles": [str(e)[:80]]}
            detalles_totales.append(f"{criterio}: {str(e)[:50]}")

    return {
        "enviados": total_env,
        "fallidos": total_fal,
        "detalles": detalles_totales,
        "resultados": resultados,
    }
