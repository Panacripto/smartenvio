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
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "facturadigital_config.json")
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except:
        return {}


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


@router.get("")
def listar_campanas():
    return sqlite_query("SELECT * FROM campaigns ORDER BY created_at DESC")


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
    cid = sqlite_execute("""
        INSERT INTO campaigns (nombre, mensaje, intervalo, fecha_inicio, fecha_fin,
                               hora_envio, hora_fin, repetir_cada, clientes_seleccionados, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (body.nombre, body.mensaje, body.intervalo, body.fecha_inicio, body.fecha_fin,
          body.hora_envio, body.hora_fin, body.repetir_cada, json.dumps(body.clientes_seleccionados), now, now))
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
    if body.activo is not None:
        campos["activo"] = 1 if body.activo else 0
    if campos:
        set_parts = ", ".join(f"{k}=?" for k in campos)
        vals = list(campos.values()) + [camp_id]
        sqlite_execute(f"UPDATE campaigns SET {set_parts}, updated_at=datetime('now') WHERE id=?", vals)
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
    sqlite_execute("UPDATE campaigns SET activo=?, updated_at=datetime('now') WHERE id=?", (nuevo, camp_id))
    return {"ok": True, "activo": bool(nuevo)}


@router.delete("/{camp_id}")
def eliminar_campana(camp_id: int):
    sqlite_execute("DELETE FROM campaign_attachments WHERE campaign_id=?", (camp_id,))
    sqlite_execute("DELETE FROM campaign_log WHERE campaign_id=?", (camp_id,))
    sqlite_execute("DELETE FROM campaigns WHERE id=?", (camp_id,))
    return {"ok": True}


# --- Scheduler ---

def _obtener_clientes_por_codigos(codigos: list[str]) -> list[dict]:
    if not codigos:
        return []
    sql = "SELECT FC_CODIGO, FC_DESCRIPCION, FC_TELEFONO FROM Sclientes WHERE FC_CODIGO IN ({})".format(
        ",".join("'{}'".format(c.replace("'", "''")) for c in codigos)
    )
    return odbc_connector.query(sql)


def _ejecutar_campana(camp: dict):
    try:
        codigos = json.loads(camp.get("clientes_seleccionados") or "[]")
        if not codigos:
            return
        clientes = _obtener_clientes_por_codigos(codigos)
        if not clientes:
            return

        # MARCA como ejecutada ANTES de enviar para evitar loop infinito
        num = (camp.get("veces_ejecutada") or 0) + 1
        sqlite_execute("UPDATE campaigns SET veces_ejecutada=?, ultima_ejecucion=datetime('now') WHERE id=?",
                      (num, camp["id"]))

        empresa_cfg = _load_empresa_config()
        adjuntos = sqlite_query("SELECT * FROM campaign_attachments WHERE campaign_id=?", (camp["id"],))
        enviados = 0
        fallidos = 0
        detalles = []
        plantilla = camp.get("mensaje", "")
        for cli in clientes:
            tel = str(cli.get("FC_TELEFONO") or "").replace(" ", "").replace("-", "")
            if not tel:
                continue
            msg = plantilla
            msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", ""))
            msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", ""))
            for k, v in cli.items():
                msg = msg.replace("{" + k + "}", str(v or ""))
            try:
                payload = {"telefono": tel, "mensaje": msg}
                if adjuntos:
                    for adj in adjuntos:
                        payload["archivo_base64"] = adj["archivo_base64"]
                        payload["archivo_nombre"] = adj["archivo_nombre"]
                        payload["archivo_mimetype"] = adj["archivo_mimetype"] or "application/octet-stream"
                        resp = httpx.post(f"{settings.whatsapp_service_url}/api/send", json=payload, timeout=300)
                        if resp.status_code >= 400:
                            raise Exception(resp.text)
                else:
                    resp = httpx.post(f"{settings.whatsapp_service_url}/api/send", json=payload, timeout=300)
                    if resp.status_code >= 400:
                        raise Exception(resp.text)
                enviados += 1
                detalles.append(f"\u2713 {cli.get('FC_DESCRIPCION', tel)}")
            except Exception as e:
                fallidos += 1
                detalles.append(f"\u2717 {cli.get('FC_DESCRIPCION', tel)}: {str(e)[:80]}")
            time.sleep(0.3)

        sqlite_execute("UPDATE campaigns SET enviados_total=enviados_total+?, fallidos_total=fallidos_total+? WHERE id=?",
                      (enviados, fallidos, camp["id"]))
        sqlite_execute("INSERT INTO campaign_log (campaign_id, ejecucion_numero, enviados, fallidos, total_destinos, detalles) VALUES (?, ?, ?, ?, ?, ?)",
                      (camp["id"], num, enviados, fallidos, len(clientes), json.dumps(detalles)))
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
    ult = camp.get("ultima_ejecucion") or ""
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
