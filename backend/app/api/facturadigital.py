import threading
import time
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query as sqlite_query, query_one, execute as sqlite_execute
from app.config import settings
from app.services.pdf_generator import generar_factura_pdf

router = APIRouter()

DEFAULT_MENSAJE = "Estimado: {cliente} hemos emitido la siguiente(s) facturas a su nombre:\n{facturas}"

DEFAULT_CONFIG = {
    "mensaje": DEFAULT_MENSAJE,
    "auto_activo": True,
    "auto_intervalo": 5,
    "enviar_pdf": True,
    "incluir_sello": True,
    "formato_pdf": "carta",
    "empresa_razon_social": "MI EMPRESA, C.A.",
    "empresa_rif": "J-12345678-9",
    "empresa_direccion": "Av. Principal, Edificio Empresa, Piso 1",
    "empresa_telefono": "0212-1234567",
    "empresa_logo": "",
    "telefono_catchall": "",
    "catchall_activo": False,
}


def _load_config():
    row = query_one("SELECT * FROM config_facturadigital WHERE id=1")
    if not row:
        return dict(DEFAULT_CONFIG)
    cfg = {}
    for k in DEFAULT_CONFIG:
        val = row.get(k)
        if val is None:
            val = DEFAULT_CONFIG[k]
        cfg[k] = val
    cfg["auto_activo"] = bool(cfg["auto_activo"])
    cfg["enviar_pdf"] = bool(cfg["enviar_pdf"])
    cfg["incluir_sello"] = bool(cfg["incluir_sello"])
    cfg["formato_pdf"] = cfg.get("formato_pdf", "carta") or "carta"
    cfg["catchall_activo"] = bool(cfg.get("catchall_activo", False))
    return cfg


def _save_config(data: dict):
    sqlite_execute("""UPDATE config_facturadigital SET
        mensaje=?, auto_activo=?, auto_intervalo=?, enviar_pdf=?, incluir_sello=?,
        formato_pdf=?, empresa_razon_social=?, empresa_rif=?, empresa_direccion=?, empresa_telefono=?, empresa_logo=?,
        telefono_catchall=?, catchall_activo=?""",
        (data.get("mensaje", ""), 1 if data.get("auto_activo") else 0, data.get("auto_intervalo", 5),
         1 if data.get("enviar_pdf", True) else 0, 1 if data.get("incluir_sello", True) else 0,
         data.get("formato_pdf", "carta"),
         data.get("empresa_razon_social", ""), data.get("empresa_rif", ""),
         data.get("empresa_direccion", ""), data.get("empresa_telefono", ""), data.get("empresa_logo", ""),
         data.get("telefono_catchall", ""), 1 if data.get("catchall_activo") else 0))


def _formatear_fecha(f):
    if hasattr(f, "strftime"):
        return f.strftime("%d/%m/%Y")
    return str(f or "").split(" ")[0]


class MensajeConfig(BaseModel):
    mensaje: str
    auto_activo: bool = False
    auto_intervalo: int = 5
    enviar_pdf: bool = True
    incluir_sello: bool = True
    formato_pdf: str = "carta"
    empresa_razon_social: str = ""
    empresa_rif: str = ""
    empresa_direccion: str = ""
    empresa_telefono: str = ""
    empresa_logo: str = ""
    telefono_catchall: str = ""
    catchall_activo: bool = False


@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config")
def set_config(body: MensajeConfig):
    if body.catchall_activo and not body.telefono_catchall.strip():
        raise HTTPException(400, "Debes escribir un teléfono catch-all o desactivar la opción")
    _save_config(body.model_dump())
    return {"ok": True}


def _query_facturas(search: str = "", filtro: str = "", desde: str = "", hasta: str = ""):
    sql = """
        SELECT
            o.FTI_DOCUMENTO,
            o.FTI_FECHAEMISION,
            o.FTI_MONEDA,
            o.FTI_FACTORREFERENCIA,
            o.FTI_RESPONSABLE,
            o.FTI_PERSONACONTACTO,
            o.FTI_TELEFONOCONTACTO,
            o.FTI_TOTALNETO,
            o.FTI_SALDOOPERACION,
            o.FTI_RIFCLIENTE,
            o.FTI_IMPUESTO1PORCENT,
            c.FC_TELEFONO,
            c.FC_DESCRIPCION as FC_DESCRIPCION,
            CASE WHEN o.FTI_MONEDA = 1 THEN o.FTI_BASEIMPONIBLE / o.FTI_FACTORREFERENCIA ELSE o.FTI_BASEIMPONIBLE END AS BI_DIVISA,
            CASE WHEN o.FTI_MONEDA = 1 THEN o.FTI_IMPUESTO1MONTO / o.FTI_FACTORREFERENCIA ELSE o.FTI_IMPUESTO1MONTO END AS IVA_DIVISA,
            CASE WHEN o.FTI_MONEDA = 1 THEN o.FTI_TOTALNETO / o.FTI_FACTORREFERENCIA ELSE o.FTI_TOTALNETO END AS TOTAL_DIVISA,
            CASE WHEN o.FTI_MONEDA = 1 THEN o.FTI_SALDOOPERACION / o.FTI_FACTORREFERENCIA ELSE o.FTI_SALDOOPERACION END AS SALDO_DIVISA
        FROM SOperacionInv o
        LEFT JOIN Sclientes c ON c.FC_CODIGO = o.FTI_RESPONSABLE
        WHERE o.FTI_TIPO = 11 AND o.FTI_STATUS = 1
    """
    if filtro == "hoy":
        sql += " AND o.FTI_FECHAEMISION >= CURRENT_DATE AND o.FTI_FECHAEMISION < CURRENT_DATE + 1"
    elif filtro == "semana":
        lunes = date.today() - timedelta(days=date.today().weekday())
        domingo = lunes + timedelta(days=7)
        sql += " AND o.FTI_FECHAEMISION >= '{}' AND o.FTI_FECHAEMISION < '{}'".format(lunes, domingo)
    elif filtro == "mes":
        primero = date.today().replace(day=1)
        sql += " AND o.FTI_FECHAEMISION >= '{}'".format(primero)
    elif filtro == "anio":
        primero = date.today().replace(month=1, day=1)
        sql += " AND o.FTI_FECHAEMISION >= '{}'".format(primero)
    elif filtro == "personalizado":
        if desde:
            d = desde.replace("'", "''")
            sql += " AND o.FTI_FECHAEMISION >= '{}'".format(d)
        if hasta:
            h = hasta.replace("'", "''")
            sql += " AND o.FTI_FECHAEMISION <= '{}'".format(h)
    if search:
        escaped = search.replace("'", "''").upper()
        sql += " AND (UPPER(o.FTI_DOCUMENTO) LIKE '%{}%' OR UPPER(o.FTI_RESPONSABLE) LIKE '%{}%' OR UPPER(o.FTI_PERSONACONTACTO) LIKE '%{}%' OR UPPER(c.FC_DESCRIPCION) LIKE '%{}%')".format(
            escaped, escaped, escaped, escaped
        )
    sql += " ORDER BY o.FTI_DOCUMENTO DESC"
    return odbc_connector.query(sql)


@router.get("")
def listar_facturas(search: str = "", filtro: str = "", desde: str = "", hasta: str = ""):
    facturas = _query_facturas(search, filtro, desde, hasta)

    envios = {}
    try:
        for row in sqlite_query("SELECT documento, enviado_en, estado FROM factura_digital_envios WHERE estado IS NULL OR estado NOT IN ('pendiente','fallido')"):
            envios[row["documento"]] = row
    except:
        for row in sqlite_query("SELECT documento, enviado_en, estado FROM factura_digital_envios"):
            envios[row["documento"]] = row

    for f in facturas:
        e = envios.get(f["FTI_DOCUMENTO"])
        if e:
            f["enviado"] = True
            f["enviado_en"] = e.get("enviado_en", "")
            f["envio_estado"] = e.get("estado", "")
        else:
            f["enviado"] = False
            f["enviado_en"] = None
            f["envio_estado"] = None
        f["sin_telefono"] = not (f.get("FTI_TELEFONOCONTACTO") or f.get("FC_TELEFONO") or "")

    return facturas


# Limpiar registros huérfanos que quedaron del experimento ACK
try:
    sqlite_execute("DELETE FROM factura_digital_envios WHERE estado='pendiente' OR estado='fallido' OR estado='enviando'")
except:
    pass


def _normalizar_tel(tel: str) -> str:
    tel = tel.replace(" ", "").replace("-", "").replace("+", "")
    if tel.startswith("0") and len(tel) == 11:
        return "58" + tel[1:]
    return tel


def _query_detail(doc: str) -> list[dict]:
    escaped = doc.replace("'", "''")
    sql = """
        SELECT d.FDI_LINEA, d.FDI_CODIGO, d.FDI_CANTIDAD, d.FDI_PRECIODEVENTA,
               d.FDI_MONEDA, d.FDI_FACTORCAMBIO,
               d.FDI_MONTOIMPUESTO1, d.FDI_DESCRIPCIONOFERTA,
               i.FI_DESCRIPCION AS producto_desc, i.FI_UNIDAD
        FROM SDetalleVenta d
        LEFT JOIN Sinventario i ON i.FI_CODIGO = d.FDI_CODIGO
        WHERE d.FDI_DOCUMENTO = '{}'
        ORDER BY d.FDI_LINEA
    """.format(escaped)
    return odbc_connector.query(sql)


def _query_cliente(codigo: str) -> dict | None:
    escaped = codigo.replace("'", "''")
    sql = """
        SELECT FC_DESCRIPCION, FC_RIF, FC_DIRECCION1, FC_DIRECCION2, FC_DIRECCION3,
               FC_TELEFONO, FC_CONTACTO
        FROM Sclientes WHERE FC_CODIGO = '{}'
    """.format(escaped)
    rows = odbc_connector.query(sql)
    return rows[0] if rows else None


def _procesar_y_enviar(facturas_pendientes: list) -> dict:
    """Envía cada factura como PDF adjunto + mensaje de texto."""
    if not facturas_pendientes:
        return {"enviados": 0, "fallidos": 0, "detalles": []}

    config = _load_config()
    formato_pdf = config.get("formato_pdf", "carta")
    plantilla = config.get("mensaje", DEFAULT_MENSAJE)
    catchall_tel = _normalizar_tel(config.get("telefono_catchall", "")) if config.get("catchall_activo") else None

    enviados = 0
    fallidos = 0
    detalles = []
    docs_enviados_ahora: list[tuple[str, str, str]] = []

    sin_telefono = 0
    for f in facturas_pendientes:
        doc = f["FTI_DOCUMENTO"]
        tel = _normalizar_tel(str(f.get("FTI_TELEFONOCONTACTO") or f.get("FC_TELEFONO") or ""))
        if not tel:
            sin_telefono += 1
            try:
                sqlite_execute("INSERT OR REPLACE INTO factura_digital_envios (documento, telefono, cliente_codigo, estado) VALUES (?, ?, ?, 'no_phone')",
                              (doc, "", f.get("FTI_RESPONSABLE", "")))
            except:
                pass
            detalles.append(f"X {doc}: sin telefono")
            continue

        cliente = f.get("FTI_PERSONACONTACTO") or f.get("FC_DESCRIPCION") or f.get("FTI_RESPONSABLE") or ""
        doc = f["FTI_DOCUMENTO"]
        fecha = _formatear_fecha(f["FTI_FECHAEMISION"])
        factor = f.get("FTI_FACTORREFERENCIA") or 1

        # Calcular total BS desde cabecera
        total_neto = float(f.get("FTI_TOTALNETO") or 0)
        moneda_f = int(f.get("FTI_MONEDA") or 0)
        factor_f = float(f.get("FTI_FACTORREFERENCIA") or 1)
        if factor_f == 0:
            factor_f = 1
        if moneda_f == 2:
            total_bs = total_neto * factor_f
        else:
            total_bs = total_neto
        total_usd = total_bs / factor if factor else total_bs

        # Generar PDF (solo si esta habilitado)
        enviar_pdf = config.get("enviar_pdf", True)
        pdf_b64 = None
        if enviar_pdf:
            try:
                detail = _query_detail(doc)
                client_data = _query_cliente(f.get("FTI_RESPONSABLE", ""))
                pdf_b64 = generar_factura_pdf(f, detail, client_data, config, formato=formato_pdf)
            except Exception as e:
                fallidos += 1
                detalles.append(f"Error generando PDF {doc}: {e}")
                continue

        # Mensaje de texto
        mensaje = plantilla
        mensaje = mensaje.replace("{empresa_razon_social}", config.get("empresa_razon_social", ""))
        mensaje = mensaje.replace("{empresa_rif}", config.get("empresa_rif", ""))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            mensaje = mensaje.replace("{" + k + "}", v)
        mensaje = mensaje.replace("{cliente}", cliente)
        mensaje = mensaje.replace("{facturas}",
            f"DOCUMENTO: {doc}\nFECHA: {fecha}\nTOTAL$: {total_usd:.2f}\nTASA: {factor:.2f}\nTOTAL Bs.: {total_bs:.2f}")

        payload = {"telefono": tel, "mensaje": mensaje}
        if pdf_b64:
            payload["archivo_base64"] = pdf_b64
            payload["archivo_nombre"] = f"factura_{doc}.pdf"
            payload["archivo_mimetype"] = "application/pdf"

        try:
            resp = httpx.post(f"{settings.whatsapp_service_url}/api/send",
                json=payload, timeout=60)
            if resp.status_code == 200:
                enviados += 1
                docs_enviados_ahora.append((doc, tel, f.get("FTI_RESPONSABLE", "")))
                if catchall_tel:
                    try:
                        payload_catch = dict(payload)
                        payload_catch["telefono"] = catchall_tel
                        httpx.post(f"{settings.whatsapp_service_url}/api/send",
                                   json=payload_catch, timeout=60)
                    except:
                        pass
            else:
                fallidos += 1
                body = resp.text[:500] if resp.text else "(vacio)"
                detalles.append(f"Error enviando {doc}: {resp.status_code} - {body}")
        except Exception as e:
            fallidos += 1
            detalles.append(f"Error conexion {doc}: {e}")

        for doc, tel, resp_codigo in docs_enviados_ahora:
            try:
                sqlite_execute("INSERT OR REPLACE INTO factura_digital_envios (documento, telefono, cliente_codigo, estado) VALUES (?, ?, ?, 'sent')", (doc, tel, resp_codigo))
            except:
                pass

    return {"enviados": enviados, "fallidos": fallidos, "sin_telefono": sin_telefono, "detalles": detalles}


class EnviarSeleccionadosBody(BaseModel):
    documentos: list[str]

@router.post("/enviar-seleccionados")
def enviar_seleccionados(body: EnviarSeleccionadosBody):
    if not body.documentos:
        raise HTTPException(400, "No hay facturas seleccionadas")
    docs = body.documentos
    todos = _query_facturas()
    seleccionadas = [f for f in todos if f["FTI_DOCUMENTO"] in docs]
    if not seleccionadas:
        raise HTTPException(400, "Ninguna factura seleccionada existe")
    try:
        docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios WHERE estado IS NULL OR estado NOT IN ('pendiente','fallido')"))
    except:
        docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios"))
    pendientes = [f for f in seleccionadas if f["FTI_DOCUMENTO"] not in docs_enviados]
    if not pendientes:
        return {"enviados": 0, "fallidos": 0, "sin_telefono": 0, "omitidos": len(seleccionadas), "detalles": ["Todas fueron enviadas"]}
    result = _procesar_y_enviar(pendientes)
    omitidos = len(seleccionadas) - len(pendientes)
    if omitidos > 0:
        result["omitidos"] = omitidos
    return result

@router.post("/enviar")
def enviar_facturas(search: str = "", filtro: str = "", desde: str = "", hasta: str = ""):
    facturas = _query_facturas(search, filtro, desde, hasta)
    if not facturas:
        raise HTTPException(400, "No hay facturas para enviar")

    try:
        docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios WHERE estado IS NULL OR estado NOT IN ('pendiente','fallido')"))
    except:
        docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios"))
    pendientes = [f for f in facturas if f["FTI_DOCUMENTO"] not in docs_enviados]
    omitidos = len(facturas) - len(pendientes)

    if not pendientes:
        return {"enviados": 0, "fallidos": 0, "omitidos": omitidos, "detalles": ["Todas fueron enviadas"]}

    result = _procesar_y_enviar(pendientes)
    if omitidos > 0:
        result["omitidos"] = omitidos
    return result


@router.delete("/envio/{documento}")
def eliminar_envio(documento: str):
    """Elimina el registro de envio para que la factura pueda reenviarse."""
    sqlite_execute("DELETE FROM factura_digital_envios WHERE documento=?", (documento,))
    return {"ok": True}


@router.get("/metrics")
def metrics():
    facturas = _query_facturas()
    envios = {}
    try:
        for row in sqlite_query("SELECT documento, estado FROM factura_digital_envios"):
            envios[row["documento"]] = row.get("estado", "")
    except:
        for row in sqlite_query("SELECT documento FROM factura_digital_envios"):
            envios[row["documento"]] = "sent"

    total = len(facturas)
    enviadas = 0
    confirmadas = 0
    fallidas = 0
    sin_tel = 0
    pendientes = 0
    for f in facturas:
        doc = f["FTI_DOCUMENTO"]
        if doc in envios:
            est = envios[doc]
            if est in (None, "", "sent", "enviado"):
                enviadas += 1
            elif est == "confirmado":
                confirmadas += 1
            elif est == "fallido":
                fallidas += 1
            elif est == "no_phone":
                sin_tel += 1
            else:
                enviadas += 1
        else:
            if f.get("FTI_TELEFONOCONTACTO") or f.get("FC_TELEFONO"):
                pendientes += 1
            else:
                sin_tel += 1

    return {
        "total": total,
        "enviadas": enviadas,
        "confirmadas": confirmadas,
        "fallidas": fallidas,
        "sin_telefono": sin_tel,
        "pendientes": pendientes,
    }


@router.get("/envios")
def listar_envios():
    """Retorna el historial de envíos."""
    try:
        return sqlite_query("SELECT * FROM factura_digital_envios ORDER BY rowid DESC LIMIT 200")
    except:
        return []


@router.get("/auto-status")
def auto_status():
    """Diagnostico del auto-envio."""
    hilos = [t.name for t in threading.enumerate()]
    cfg = _load_config()
    return {
        "auto_activo": cfg.get("auto_activo"),
        "auto_intervalo": cfg.get("auto_intervalo"),
        "hilos_activos": hilos,
    }


# --- Auto-envío en segundo plano ---
_auto_thread = None
_auto_detener = False


def _auto_loop():
    global _auto_detener
    while not _auto_detener:
        try:
            cfg = _load_config()
            if cfg.get("auto_activo"):
                try:
                    docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios WHERE estado IS NULL OR estado NOT IN ('pendiente','fallido','enviando')"))
                except:
                    docs_enviados = set(r["documento"] for r in sqlite_query("SELECT DISTINCT documento FROM factura_digital_envios"))
                hoy = _query_facturas(filtro="hoy")
                pendientes = [f for f in hoy if f["FTI_DOCUMENTO"] not in docs_enviados]
                if pendientes:
                    # Marcar como "enviando" ANTES de enviar para evitar loop
                    for f in pendientes:
                        try:
                            sqlite_execute("INSERT OR IGNORE INTO factura_digital_envios (documento, telefono, cliente_codigo, estado) VALUES (?, ?, ?, 'enviando')",
                                          (f["FTI_DOCUMENTO"], f.get("FTI_TELEFONOCONTACTO") or f.get("FC_TELEFONO") or "", f.get("FTI_RESPONSABLE", "")))
                        except:
                            pass
                    _procesar_y_enviar(pendientes)
            intervalo = cfg.get("auto_intervalo", 5)
            for _ in range(intervalo * 6):
                if _auto_detener:
                    break
                time.sleep(10)
        except:
            time.sleep(60)


def iniciar_auto_envio():
    global _auto_thread, _auto_detener
    _auto_detener = False
    _auto_thread = threading.Thread(target=_auto_loop, daemon=True)
    _auto_thread.start()


def detener_auto_envio():
    global _auto_detener
    _auto_detener = True


iniciar_auto_envio()
