import json, threading, time, os
from datetime import datetime, date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.database.sqlite_connector import query as sqlite_query, query_one as sqlite_query_one, execute as sqlite_execute
from app.database.odbc_connector import odbc_connector
from app.config import settings

router = APIRouter()

def _load_empresa_config():
    from app.database.sqlite_connector import query_one
    row = query_one("SELECT empresa_razon_social, empresa_rif FROM config_facturadigital WHERE id=1")
    return {"empresa_razon_social": row["empresa_razon_social"] if row else "",
            "empresa_rif": row["empresa_rif"] if row else ""}


class CampaignCreate(BaseModel):
    nombre: str
    mensaje: str = ""
    intervalo: str = "diario"
    fecha_inicio: str = ""
    fecha_fin: str = ""
    hora_envio: str = ""
    hora_fin: str = ""
    repetir_cada: int = 0
    clientes_seleccionados: list[str] = []
    adjuntos: list[dict] = []
    filtro: dict | None = None


class CampaignUpdate(BaseModel):
    nombre: str | None = None
    mensaje: str | None = None
    intervalo: str | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    hora_envio: str | None = None
    hora_fin: str | None = None
    repetir_cada: int | None = None
    activo: bool | None = None
    clientes_seleccionados: list[str] | None = None
    adjuntos: list[dict] | None = None
    filtro: dict | None = None


@router.get("")
def listar_campanas(filtro: str = "todas", q: str = "", page: int = 1, per_page: int = 20):
    where = []
    params = []
    hoy = date.today().isoformat()

    if filtro == "activas":
        where.append("(fecha_fin = '' OR fecha_fin >= ?)")
        params.append(hoy)
    elif filtro == "finalizadas":
        where.append("(fecha_fin != '' AND fecha_fin < ?)")
        params.append(hoy)

    if q:
        where.append("nombre LIKE ?")
        params.append(f"%{q}%")

    w = " WHERE " + " AND ".join(where) if where else ""
    total = sqlite_query_one(f"SELECT COUNT(*) as total FROM campaigns{w}", params)["total"]
    offset = (page - 1) * per_page
    rows = sqlite_query(f"SELECT * FROM campaigns{w} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        params + [per_page, offset])
    return {"total": total, "page": page, "per_page": per_page, "data": rows}

@router.get("/{camp_id}/detail")
def detalle_campana(camp_id: int):
    c = sqlite_query_one("SELECT * FROM campaigns WHERE id=?", (camp_id,))
    if not c:
        raise HTTPException(404, "Campaña no encontrada")
    c["adjuntos"] = sqlite_query("SELECT id, archivo_nombre, archivo_mimetype FROM campaign_attachments WHERE campaign_id=?", (camp_id,))
    c["log"] = sqlite_query("SELECT * FROM campaign_log WHERE campaign_id=? ORDER BY ejecucion_numero DESC", (camp_id,))
    try:
        c["filtro_obj"] = json.loads(c["filtro"]) if c.get("filtro") and c["filtro"] != "null" else None
    except:
        c["filtro_obj"] = None
    try:
        c["total_seleccionados"] = len(json.loads(c.get("clientes_seleccionados") or "[]"))
    except:
        c["total_seleccionados"] = 0
    total_enviados = sqlite_query_one("SELECT COALESCE(SUM(enviados),0) as t, COALESCE(SUM(fallidos),0) as f, COALESCE(SUM(total_destinos),0) as d FROM campaign_log WHERE campaign_id=?", (camp_id,))
    if total_enviados:
        c["total_enviados_acum"] = total_enviados["t"]
        c["total_fallidos_acum"] = total_enviados["f"]
        c["total_destinos_acum"] = total_enviados["d"]
    else:
        c["total_enviados_acum"] = c["total_fallidos_acum"] = c["total_destinos_acum"] = 0
    return c


@router.get("/debug/scheduler")
def debug_scheduler():
    import threading
    hilos = [t.name for t in threading.enumerate() if "camp" in t.name.lower()]
    return {
        "loop_count": _camp_loop_count,
        "scheduler_alive": any(t.is_alive() for t in threading.enumerate() if "camp" in t.name.lower()),
        "threads": hilos,
    }


@router.get("/{camp_id}")
def obtener_campana(camp_id: int):
    c = sqlite_query_one("SELECT * FROM campaigns WHERE id=?", (camp_id,))
    if not c:
        raise HTTPException(404, "Campaña no encontrada")
    c["adjuntos"] = sqlite_query("SELECT * FROM campaign_attachments WHERE campaign_id=?", (camp_id,))
    c["log"] = sqlite_query("SELECT * FROM campaign_log WHERE campaign_id=? ORDER BY ejecucion_numero DESC", (camp_id,))
    return c


@router.post("")
def crear_campana(body: CampaignCreate):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filtro_str = json.dumps(body.filtro) if body.filtro else None
    cid = sqlite_execute("""
        INSERT INTO campaigns (nombre, mensaje, intervalo, fecha_inicio, fecha_fin,
                               hora_envio, hora_fin, repetir_cada, clientes_seleccionados, filtro, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (body.nombre, body.mensaje, body.intervalo, body.fecha_inicio, body.fecha_fin,
          body.hora_envio, body.hora_fin, body.repetir_cada, json.dumps(body.clientes_seleccionados), filtro_str, now, now))
    for adj in body.adjuntos:
        sqlite_execute("""
            INSERT INTO campaign_attachments (campaign_id, archivo_nombre, archivo_base64, archivo_mimetype)
            VALUES (?, ?, ?, ?)
        """, (cid, adj.get("archivo_nombre", ""), adj.get("archivo_base64", ""), adj.get("archivo_mimetype", "")))
    return {"ok": True, "id": cid}


@router.put("/{camp_id}")
def actualizar_campana(camp_id: int, body: CampaignUpdate):
    c = sqlite_query_one("SELECT * FROM campaigns WHERE id=?", (camp_id,))
    if not c:
        raise HTTPException(404, "Campaña no encontrada")
    campos = {}
    for k in ("nombre", "mensaje", "intervalo", "fecha_inicio", "fecha_fin", "hora_envio", "hora_fin", "repetir_cada"):
        v = getattr(body, k, None)
        if v is not None:
            campos[k] = v
    if body.clientes_seleccionados is not None:
        campos["clientes_seleccionados"] = json.dumps(body.clientes_seleccionados)
        # Si hay clientes seleccionados manualmente, limpiar filtro
        if body.clientes_seleccionados:
            campos["filtro"] = None
    if body.filtro is not None:
        campos["filtro"] = json.dumps(body.filtro)
    if body.activo is not None:
        campos["activo"] = 1 if body.activo else 0
    if campos:
        set_parts = ", ".join(f"{k}=?" for k in campos)
        vals = list(campos.values()) + [camp_id]
        sqlite_execute(f"UPDATE campaigns SET {set_parts}, updated_at=datetime('now','localtime') WHERE id=?", vals)
    if body.adjuntos is not None:
        sqlite_execute("DELETE FROM campaign_attachments WHERE campaign_id=?", (camp_id,))
        for adj in body.adjuntos:
            sqlite_execute("INSERT INTO campaign_attachments (campaign_id, archivo_nombre, archivo_base64, archivo_mimetype) VALUES (?, ?, ?, ?)",
                          (camp_id, adj.get("archivo_nombre", ""), adj.get("archivo_base64", ""), adj.get("archivo_mimetype", "")))
    return {"ok": True}


@router.put("/{camp_id}/toggle")
def toggle_campana(camp_id: int):
    c = sqlite_query_one("SELECT * FROM campaigns WHERE id=?", (camp_id,))
    if not c:
        raise HTTPException(404, "Campaña no encontrada")
    nuevo = 0 if c["activo"] else 1
    sqlite_execute("UPDATE campaigns SET activo=?, updated_at=datetime('now','localtime') WHERE id=?", (nuevo, camp_id))
    return {"ok": True, "activo": bool(nuevo)}


@router.delete("/{camp_id}")
def eliminar_campana(camp_id: int):
    sqlite_execute("DELETE FROM campaign_attachments WHERE campaign_id=?", (camp_id,))
    sqlite_execute("DELETE FROM campaign_log WHERE campaign_id=?", (camp_id,))
    sqlite_execute("DELETE FROM campaigns WHERE id=?", (camp_id,))
    return {"ok": True}


# --- Filtros dinámicos ---

def _resolver_por_filtro(filtro: dict) -> list[dict]:
    tipo = filtro.get("tipo", "")
    texto_criterio = "PENDIENTES"
    condiciones_extra = ""
    if tipo == "facturas_vencidas":
        condiciones_extra = "AND x.FCC_FECHAVENCIMIENTO < CURRENT_DATE"
        texto_criterio = "VENCIDAS"
    elif tipo == "por_vencer":
        dias = filtro.get("dias", 7)
        condiciones_extra = "AND x.FCC_FECHAVENCIMIENTO BETWEEN CURRENT_DATE AND DATE('now', '+{} days')".format(dias)
        texto_criterio = f"POR VENCER ({dias} DÍAS)"
    elif tipo == "con_saldo":
        condiciones_extra = "AND 1=1"
    elif tipo == "saldo_mayor_que":
        valor = filtro.get("valor", 0)
        condiciones_extra = "AND 1=1"
        having_extra = "HAVING COALESCE(SUM(x.FCC_SALDOMONEDAEXT), 0) > {}".format(valor)
    elif tipo == "vencidas_saldo_mayor_que":
        valor = filtro.get("valor", 0)
        condiciones_extra = "AND x.FCC_FECHAVENCIMIENTO < CURRENT_DATE"
        texto_criterio = "VENCIDAS"
        having_extra = "HAVING COALESCE(SUM(x.FCC_SALDOMONEDAEXT), 0) > {}".format(valor)
    sql = """
        SELECT c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO,
               COALESCE(SUM(x.FCC_SALDOMONEDAEXT), 0) as FC_SALDO_TOTAL,
               COUNT(*) as FC_DOCUMENTOS
        FROM Sclientes c
        INNER JOIN Scuentasxcobrar x ON c.FC_CODIGO = x.FCC_CODIGO
        WHERE x.FCC_SALDOMONEDAEXT > 0
          AND c.FC_TELEFONO IS NOT NULL AND c.FC_TELEFONO <> ''
    """
    if condiciones_extra:
        sql += " " + condiciones_extra
    sql += " GROUP BY c.FC_CODIGO, c.FC_DESCRIPCION, c.FC_TELEFONO"
    having = locals().get("having_extra", "")
    if having:
        sql += " " + having
    try:
        rows = odbc_connector.query(sql)
        for row in rows:
            row["FC_CRITERIO"] = texto_criterio
        return rows
    except Exception as e:
        print(f"Error en filtro {tipo}: {e}")
        return []


@router.post("/preview-filter")
def previsualizar_filtro(filtro: dict):
    """Returns estimated count and sample clients for a given filter."""
    try:
        clientes = _resolver_por_filtro(filtro)
        return {"total": len(clientes), "clientes": clientes[:20]}
    except Exception as e:
        raise HTTPException(400, str(e))


# --- Scheduler ---

def _obtener_clientes_por_codigos(codigos: list[str]) -> list[dict]:
    if not codigos:
        return []
    odbc_codes = [c for c in codigos if not c.startswith("CONTACTO_")]
    contacto_ids = [int(c.replace("CONTACTO_", "")) for c in codigos if c.startswith("CONTACTO_")]
    resultados = []
    if odbc_codes:
        sql = "SELECT FC_CODIGO, FC_DESCRIPCION, FC_TELEFONO FROM Sclientes WHERE FC_CODIGO IN ({})".format(
            ",".join("'{}'".format(c.replace("'", "''")) for c in odbc_codes)
        )
        resultados.extend(odbc_connector.query(sql))
    for cid in contacto_ids:
        c = sqlite_query_one("SELECT id, nombre, telefono FROM contactos WHERE id=?", (cid,))
        if c:
            resultados.append({"FC_CODIGO": f"CONTACTO_{c['id']}", "FC_DESCRIPCION": c["nombre"], "FC_TELEFONO": c["telefono"]})
    return resultados


def _ejecutar_campana(camp: dict, reintento: bool = False):
    try:
        filtro_str = camp.get("filtro")
        if filtro_str and filtro_str != "null":
            try:
                filtro_obj = json.loads(filtro_str) if isinstance(filtro_str, str) else filtro_str
                clientes = _resolver_por_filtro(filtro_obj)
            except:
                clientes = []
        else:
            codigos = json.loads(camp.get("clientes_seleccionados") or "[]")
            clientes = _obtener_clientes_por_codigos(codigos)
        if not clientes:
            return

        empresa_cfg = _load_empresa_config()
        adjuntos = sqlite_query("SELECT * FROM campaign_attachments WHERE campaign_id=?", (camp["id"],))
        enviados = 0
        fallidos = 0
        detalles = []
        servicio_caido = False
        plantilla = camp.get("mensaje", "")
        for cli in clientes:
            tel = str(cli.get("FC_TELEFONO") or "").replace(" ", "").replace("-", "")
            if not tel:
                continue
            msg = plantilla
            msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", ""))
            msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", ""))
            from app.api.rates import get_rate_vars
            for k, v in get_rate_vars().items():
                msg = msg.replace("{" + k + "}", v)
            for k, v in cli.items():
                msg = msg.replace("{" + k + "}", str(v or ""))
            try:
                payload = {"telefono": tel, "mensaje": msg}
                if adjuntos:
                    if len(adjuntos) == 1:
                        a = adjuntos[0]
                        payload["archivo_base64"] = a["archivo_base64"]
                        payload["archivo_nombre"] = a["archivo_nombre"]
                        payload["archivo_mimetype"] = a["archivo_mimetype"] or "application/octet-stream"
                    else:
                        from io import BytesIO
                        from pypdf import PdfWriter, PdfReader
                        from reportlab.lib.pagesizes import letter
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
                        from reportlab.lib.styles import getSampleStyleSheet
                        import base64
                        writer = PdfWriter()
                        for idx, a in enumerate(adjuntos):
                            try:
                                raw = base64.b64decode(a["archivo_base64"])
                                if a.get("archivo_mimetype", "").startswith("image/"):
                                    buf = BytesIO()
                                    doc = SimpleDocTemplate(buf, pagesize=letter)
                                    img = Image(BytesIO(raw), width=400, height=500)
                                    doc.build([img])
                                    buf.seek(0)
                                    reader = PdfReader(buf)
                                    for p in reader.pages:
                                        writer.add_page(p)
                                else:
                                    reader = PdfReader(BytesIO(raw))
                                    for p in reader.pages:
                                        writer.add_page(p)
                            except:
                                pass
                        combined = BytesIO()
                        writer.write(combined)
                        combined.seek(0)
                        payload["archivo_base64"] = base64.b64encode(combined.getvalue()).decode()
                        payload["archivo_nombre"] = "adjuntos_combinados.pdf"
                        payload["archivo_mimetype"] = "application/pdf"
                    resp = httpx.post(f"{settings.whatsapp_service_url}/api/send", json=payload, timeout=300)
                    if resp.status_code >= 400:
                        raise Exception(resp.text)
                else:
                    resp = httpx.post(f"{settings.whatsapp_service_url}/api/send", json=payload, timeout=300)
                    if resp.status_code >= 400:
                        raise Exception(resp.text)
                enviados += 1
                detalles.append(f"\u2713 {cli.get('FC_DESCRIPCION', tel)}")
            except httpx.ConnectError:
                fallidos += 1
                servicio_caido = True
                detalles.append(f"\u2717 {cli.get('FC_DESCRIPCION', tel)}: servicio WhatsApp no disponible")
                time.sleep(5)
            except Exception as e:
                fallidos += 1
                msg_err = str(e)[:80]
                if "reconectando" in msg_err.lower() or "not connected" in msg_err.lower():
                    servicio_caido = True
                detalles.append(f"\u2717 {cli.get('FC_DESCRIPCION', tel)}: {msg_err}")
            time.sleep(0.3)

        # Solo marca como ejecutada si al menos 1 mensaje se entregó
        if enviados > 0:
            num = (camp.get("veces_ejecutada") or 0) + 1
            sqlite_execute("UPDATE campaigns SET veces_ejecutada=?, ultima_ejecucion=datetime('now','localtime'), enviados_total=enviados_total+?, fallidos_total=fallidos_total+? WHERE id=?",
                          (num, enviados, fallidos, camp["id"]))
        elif servicio_caido:
            # WhatsApp estaba caído - programa reintento en 5 minutos
            sqlite_execute("UPDATE campaigns SET proximo_reintento=datetime('now','localtime','+5 minutes') WHERE id=?", (camp["id"],))

        sqlite_execute("INSERT INTO campaign_log (campaign_id, ejecucion_numero, enviados, fallidos, total_destinos, detalles, ejecutado_en) VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))",
                      (camp["id"], (camp.get("veces_ejecutada") or 0) + 1 if enviados > 0 else -1, enviados, fallidos, len(clientes), json.dumps(detalles)))
    except Exception as e:
        print(f"Campaign error ({camp.get('nombre')}): {e}")


def _generar_horas(hora_inicio: str, repetir_cada: int, hora_fin: str = "") -> list[str]:
    """Generate send times from hora_inicio to hora_fin with given interval."""
    try:
        hh, mm = int(hora_inicio.split(":")[0]), int(hora_inicio.split(":")[1])
        inicio = hh * 60 + mm
        tope = 24 * 60
        if hora_fin:
            try:
                fh, fm = int(hora_fin.split(":")[0]), int(hora_fin.split(":")[1])
                tope = fh * 60 + fm
            except:
                pass
        if inicio >= tope:
            return [hora_inicio]
        horas = []
        total = inicio
        while total < tope:
            horas.append(f"{total // 60:02d}:{total % 60:02d}")
            total += repetir_cada * 60
        return horas
    except:
        return [hora_inicio]


def _hora_pasada(hora_str: str) -> bool:
    try:
        hh, mm = int(hora_str.split(":")[0]), int(hora_str.split(":")[1])
        ahora = datetime.now()
        return ahora >= ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    except:
        return True


def _ya_ejecuto_en_hora_hoy(camp: dict, hora_str: str) -> bool:
    # Re-consultar de BD para obtener ultima_ejecucion actual (local time)
    c = sqlite_query_one("SELECT ultima_ejecucion FROM campaigns WHERE id=?", (camp["id"],))
    ult = (c or {}).get("ultima_ejecucion") or ""
    if not ult or ult[:10] != date.today().isoformat():
        return False
    try:
        hh, mm = int(hora_str.split(":")[0]), int(hora_str.split(":")[1])
        ult_dt = datetime.strptime(ult[:16], "%Y-%m-%d %H:%M")
        hora_dt = ult_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return ult_dt >= hora_dt
    except:
        return False


def _debe_ejecutar_hoy(camp: dict) -> bool:
    hoy = date.today().isoformat()
    if camp.get("fecha_inicio") and camp["fecha_inicio"] > hoy:
        return False
    if camp.get("fecha_fin") and camp["fecha_fin"] < hoy:
        return False
    ult = camp.get("ultima_ejecucion") or ""
    if not ult:
        return True
    intervalo = camp.get("intervalo", "diario")
    dias = {"diario": 1, "interdiario": 2, "semanal": 7, "mensual": 30}.get(intervalo, 1)
    try:
        ult_fecha = ult[:10]
        if ult_fecha != hoy:
            return (date.today() - datetime.strptime(ult_fecha, "%Y-%m-%d").date()).days >= dias
        he = (camp.get("hora_envio") or "").strip()
        if not he:
            return False
        hh, mm = int(he.split(":")[0]), int(he.split(":")[1])
        ult_dt = datetime.strptime(ult[:16], "%Y-%m-%d %H:%M")
        hora_ejec = ult_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return ult_dt < hora_ejec
    except:
        return True


def _hora_ok(camp: dict) -> bool:
    he = (camp.get("hora_envio") or "").strip()
    if not he:
        return True
    try:
        hh, mm = int(he.split(":")[0]), int(he.split(":")[1])
        ahora = datetime.now()
        tope = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return ahora >= tope
    except:
        return True


def _ya_enviado_hoy_simple(camp: dict) -> bool:
    ult = camp.get("ultima_ejecucion") or ""
    if not ult or ult[:10] != date.today().isoformat():
        return False
    he = (camp.get("hora_envio") or "").strip()
    if not he:
        return True
    try:
        hh, mm = int(he.split(":")[0]), int(he.split(":")[1])
        ult_dt = datetime.strptime(ult[:16], "%Y-%m-%d %H:%M")
        tope = ult_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return ult_dt >= tope
    except:
        return True


_camp_loop_count = 0

def _camp_loop():
    global _camp_loop_count
    while True:
        try:
            _camp_loop_count += 1
            hoy = date.today().isoformat()
            camps = sqlite_query("SELECT * FROM campaigns WHERE activo=1")
            for camp in camps:
                try:
                    if camp.get("fecha_inicio") and camp["fecha_inicio"] > hoy:
                        continue
                    if camp.get("fecha_fin") and camp["fecha_fin"] < hoy:
                        continue

                    # Reintento pendiente por servicio caído
                    prox = camp.get("proximo_reintento")
                    if prox:
                        try:
                            if datetime.strptime(prox[:19], "%Y-%m-%d %H:%M:%S") <= datetime.now():
                                _ejecutar_campana(camp, reintento=True)
                                continue
                        except:
                            pass

                    he = (camp.get("hora_envio") or "").strip()
                    repetir = camp.get("repetir_cada") or 0

                    if he and repetir > 0:
                        hf = (camp.get("hora_fin") or "").strip()
                        horas = _generar_horas(he, repetir, hf)
                        for h in horas:
                            if not _hora_pasada(h):
                                continue
                            if _ya_ejecuto_en_hora_hoy(camp, h):
                                continue
                            _ejecutar_campana(camp)
                    else:
                        if not _debe_ejecutar_hoy(camp):
                            continue
                        if not _hora_ok(camp):
                            continue
                        if _ya_enviado_hoy_simple(camp):
                            continue
                        _ejecutar_campana(camp)
                except:
                    pass
        except:
            pass
        time.sleep(60)


def iniciar_scheduler():
    hilo = threading.Thread(target=_camp_loop, daemon=True)
    hilo.start()


iniciar_scheduler()
