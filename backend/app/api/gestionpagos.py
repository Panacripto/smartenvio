import io, base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from datetime import date
from app.config import settings
from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query as sqlite_query, query_one, execute as sqlite_execute
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

router = APIRouter()

DEFAULT_MENSAJE = "Deudas a la fecha: *{fecha}*\n\n{lista_proveedores}\n\nTotal por Pagar: {total_general}"

DEFAULT_CONFIG = {
    "mensaje": DEFAULT_MENSAJE,
    "telefono1": "",
    "telefono2": "",
    "telefono3": "",
    "activo": False,
}


def _load_config():
    row = query_one("SELECT * FROM config_gestionpagos WHERE id=1")
    if not row:
        return dict(DEFAULT_CONFIG)
    cfg = {}
    for k in DEFAULT_CONFIG:
        val = row.get(k)
        if val is None:
            val = DEFAULT_CONFIG[k]
        cfg[k] = val
    cfg["activo"] = bool(cfg.get("activo", False))
    return cfg


def _save_config(data: dict):
    sqlite_execute("""UPDATE config_gestionpagos SET
        mensaje=?, telefono1=?, telefono2=?, telefono3=?, activo=?""",
        (data.get("mensaje", ""),
         data.get("telefono1", ""), data.get("telefono2", ""), data.get("telefono3", ""),
         1 if data.get("activo") else 0))


class GestionPagosConfig(BaseModel):
    mensaje: str = DEFAULT_MENSAJE
    telefono1: str = ""
    telefono2: str = ""
    telefono3: str = ""
    activo: bool = False


@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config")
def set_config(body: GestionPagosConfig):
    if body.activo and not any([body.telefono1.strip(), body.telefono2.strip(), body.telefono3.strip()]):
        raise HTTPException(400, "Debes escribir al menos un teléfono o desactivar Gestión de Pagos")
    _save_config(body.model_dump())
    return {"ok": True}


def _sync_desde_odbc():
    sql = """
        SELECT c.FCP_CODIGO, p.FP_DESCRIPCION, c.FCP_NUMERO, c.FCP_FECHAVENCIMIENTO,
               CASE WHEN c.FCP_MONEDA=1 THEN c.FCP_SALDODOCUMENTO / NULLIF(c.FCP_FACTORREFERENCIA, 0)
                    ELSE c.FCP_SALDOMONEDAEXT END AS PORPAGAR
        FROM Scuentasxpagar c
        INNER JOIN Sproveedor p ON c.FCP_CODIGO = p.FP_CODIGO
        WHERE c.FCP_TIPOTRANSACCION=1
          AND c.FCP_SALDOMONEDAEXT > 0
          AND c.FCP_SALDODOCUMENTO > 0
        ORDER BY p.FP_DESCRIPCION, c.FCP_FECHAVENCIMIENTO
    """
    rows = odbc_connector.query(sql)

    from app.database.sqlite_connector import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM pagos_documentos")
        conn.execute("DELETE FROM pagos_proveedores")
        proveedores_vistos = set()
        for r in rows:
            cod = r["FCP_CODIGO"]
            if cod not in proveedores_vistos:
                proveedores_vistos.add(cod)
                conn.execute(
                    "INSERT OR REPLACE INTO pagos_proveedores (codigo, nombre) VALUES (?, ?)",
                    (cod, r.get("FP_DESCRIPCION") or cod))
            conn.execute(
                "INSERT INTO pagos_documentos (proveedor_codigo, numero, monto, fecha_vencimiento) VALUES (?, ?, ?, ?)",
                (cod, r.get("FCP_NUMERO") or "",
                 float(r.get("PORPAGAR") or 0),
                 str(r.get("FCP_FECHAVENCIMIENTO") or "").split(" ")[0]))

    return len(rows)


@router.post("/sync")
def sync_datos():
    try:
        total = _sync_desde_odbc()
        return {"ok": True, "documentos_sincronizados": total}
    except Exception as e:
        raise HTTPException(500, f"Error al sincronizar: {str(e)}")


def _leer_desde_sqlite(criterio: str = "todas", search: str = ""):
    where_extra = ""
    if criterio == "vencidas":
        where_extra = "AND sub.dias > 0"
    elif criterio == "por_vencer":
        where_extra = "AND sub.dias <= 0"

    params: list = []
    if search:
        where_extra += " AND (sub.nombre LIKE ? OR sub.codigo LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    sql = f"""
        SELECT * FROM (
            SELECT p.codigo, p.nombre, d.numero, d.monto, d.fecha_vencimiento,
                   CAST(JULIANDAY('now') - JULIANDAY(d.fecha_vencimiento) AS INTEGER) AS dias
            FROM pagos_proveedores p
            INNER JOIN pagos_documentos d ON d.proveedor_codigo = p.codigo
        ) sub
        WHERE 1=1 {where_extra}
        ORDER BY sub.nombre, sub.fecha_vencimiento
    """
    return sqlite_query(sql, tuple(params))


def _agrupar_por_proveedor(rows: list) -> list:
    grupos = {}
    for r in rows:
        cod = r["codigo"]
        if cod not in grupos:
            grupos[cod] = {
                "codigo": cod,
                "nombre": r.get("nombre") or cod,
                "documentos": [],
                "total": 0.0,
            }
        grupos[cod]["documentos"].append({
            "numero": r.get("numero") or "",
            "monto": float(r.get("monto") or 0),
            "fecha_vencimiento": r.get("fecha_vencimiento") or "",
            "dias": int(r.get("dias") or 0),
        })
        grupos[cod]["total"] += float(r.get("monto") or 0)
    return list(grupos.values())


def _formatear_dias(dias: int) -> str:
    if dias > 0:
        return f"{dias} días vencido"
    elif dias < 0:
        return f"{abs(dias)} días por vencer"
    return "Vence hoy"


def _generar_bloque_proveedor(p: dict) -> str:
    lineas = [f"PROVEEDOR: {p['nombre']}"]
    for d in p["documentos"]:
        dias_txt = _formatear_dias(d["dias"])
        lineas.append(f"  {d['numero']} → ${d['monto']:.2f} → Vence: {d['fecha_vencimiento']} ({dias_txt})")
    lineas.append(f"  Subtotal: ${p['total']:.2f}")
    return "\n".join(lineas)


@router.get("")
def listar_gestion_pagos(search: str = "", criterio: str = "todas"):
    rows = _leer_desde_sqlite(criterio, search)
    if not rows:
        return {"proveedores": [], "total_general": 0, "cantidad_proveedores": 0, "cantidad_documentos": 0}

    proveedores = _agrupar_por_proveedor(rows)
    total_general = sum(p["total"] for p in proveedores)

    return {
        "proveedores": proveedores,
        "total_general": round(total_general, 2),
        "cantidad_proveedores": len(proveedores),
        "cantidad_documentos": sum(len(p["documentos"]) for p in proveedores),
    }


def _telefonos_activos(config: dict) -> list[str]:
    tels = []
    for k in ("telefono1", "telefono2", "telefono3"):
        t = config.get(k, "").strip()
        if t:
            tels.append(t)
    return tels


def _generar_pdf(proveedores: list, total_general: float, hoy: str, cant_docs: int, criterio: str = "todas") -> str:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    normal = styles["Normal"]
    small = ParagraphStyle("Small2", parent=styles["Normal"], fontSize=8, spaceAfter=2)

    etiquetas = {"todas": "Todas las facturas pendientes", "vencidas": "Facturas vencidas", "por_vencer": "Facturas por vencer"}
    subtitulo = etiquetas.get(criterio, "Todas las facturas pendientes")

    total_vencido = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] > 0)
    total_por_vencer = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] <= 0)

    elements = []
    elements.append(Paragraph(f"GESTIÓN DE PAGOS - {hoy}", title_style))
    elements.append(Paragraph(f"<b>{subtitulo}</b>", normal))
    if criterio == "todas":
        elements.append(Paragraph(
            f"<b>Vencido: ${total_vencido:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; Por vencer: ${total_por_vencer:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; Total general: ${total_general:,.2f}</b>",
            normal))
    else:
        elements.append(Paragraph(
            f"<b>{cant_docs} facturas de {len(proveedores)} proveedores — Total: ${total_general:,.2f}</b>",
            normal))
    elements.append(Spacer(1, 12))

    for p in proveedores:
        elements.append(Paragraph(f"<b>{p['nombre']} — ${p['total']:,.2f}</b>", normal))
        data = [["Documento", "Monto", "Vencimiento", "Días"]]
        for d in p["documentos"]:
            dias_txt = f"{d['dias']}d vencido" if d["dias"] > 0 else (f"{abs(d['dias'])}d" if d["dias"] < 0 else "hoy")
            data.append([d["numero"], f"${d['monto']:.2f}", d["fecha_vencimiento"], dias_txt])
        t = Table(data, colWidths=[1.2*inch, 1*inch, 1.2*inch, 1*inch])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))

    doc.build(elements)
    pdf_bytes = buf.getvalue()
    return base64.b64encode(pdf_bytes).decode("utf-8")


def _generar_bloque_todos(proveedores: list) -> str:
    partes = []
    for p in proveedores:
        partes.append(_generar_bloque_proveedor(p))
    return "\n".join(partes)


def _generar_lista_proveedores(proveedores: list) -> str:
    return "\n".join(f"{p['nombre']}  ${p['total']:.2f}" for p in proveedores)


@router.post("/enviar")
def enviar_gestion_pagos(criterio: str = "todas", incluir_pdf: bool = True):
    config = _load_config()
    if not config["activo"]:
        raise HTTPException(400, "Gestión de Pagos está desactivada")

    telefonos = _telefonos_activos(config)
    if not telefonos:
        raise HTTPException(400, "No hay teléfonos configurados para Gestión de Pagos")

    data = listar_gestion_pagos(criterio=criterio)
    proveedores = data["proveedores"]
    if not proveedores:
        raise HTTPException(400, "No hay proveedores con deuda pendiente")

    total_general = data["total_general"]
    hoy = date.today().strftime("%d/%m/%Y")
    plantilla = config.get("mensaje", DEFAULT_MENSAJE)

    pdf_base64 = None
    if incluir_pdf:
        try:
            pdf_base64 = _generar_pdf(proveedores, total_general, hoy, data["cantidad_documentos"], criterio)
        except:
            pdf_base64 = None

    bloque = _generar_bloque_todos(proveedores)
    lista = _generar_lista_proveedores(proveedores)
    mensaje = plantilla
    condicion_map = {"vencidas": "VENCIDAS", "por_vencer": "POR VENCER", "todas": "TODAS"}
    condicion = condicion_map.get(criterio, "PENDIENTES")
    mensaje = mensaje.replace("{fecha}", hoy)
    mensaje = mensaje.replace("{proveedores}", bloque)
    mensaje = mensaje.replace("{lista_proveedores}", lista)
    mensaje = mensaje.replace("{condicion}", condicion)
    total_vencido = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] > 0)
    total_por_vencer = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] <= 0)
    mensaje = mensaje.replace("{proveedor}", proveedores[0]["nombre"])
    mensaje = mensaje.replace("{codigo}", proveedores[0]["codigo"])
    mensaje = mensaje.replace("{total_proveedor}", f"${proveedores[0]['total']:.2f}")
    mensaje = mensaje.replace("{total_vencido}", f"${total_vencido:.2f}")
    mensaje = mensaje.replace("{total_por_vencer}", f"${total_por_vencer:.2f}")
    mensaje = mensaje.replace("{total_general}", f"${total_general:.2f}")

    enviados = 0
    fallidos = 0
    detalles = []

    for tel in telefonos:
        body = {"telefono": tel, "mensaje": mensaje}
        if pdf_base64:
            body["archivo_base64"] = pdf_base64
            body["archivo_nombre"] = f"GestionPagos_{hoy.replace('/', '')}.pdf"
            body["archivo_mimetype"] = "application/pdf"
        try:
            resp = httpx.post(
                f"{settings.whatsapp_service_url}/api/send",
                json=body,
                timeout=120,
            )
            if resp.status_code == 200:
                enviados += 1
                detalles.append(f"✓ Enviado a {tel}")
            else:
                fallidos += 1
                body_txt = resp.text[:200] if resp.text else "(vacio)"
                detalles.append(f"✗ {tel}: {resp.status_code}")
        except httpx.ConnectError:
            fallidos += 1
            detalles.append(f"✗ {tel}: servicio WhatsApp no disponible")
        except Exception as e:
            fallidos += 1
            detalles.append(f"✗ {tel}: {str(e)[:80]}")

    return {"enviados": enviados, "fallidos": fallidos, "detalles": detalles}


@router.get("/proveedores-agrupados")
def proveedores_agrupados(criterio: str = "todas"):
    data = listar_gestion_pagos(criterio=criterio)
    return data if isinstance(data, dict) else {"proveedores": [], "total_general": 0, "cantidad_proveedores": 0, "cantidad_documentos": 0}
