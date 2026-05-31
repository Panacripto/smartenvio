import os, tempfile, base64, json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.config import settings

router = APIRouter()

def _load_empresa_config():
    from app.database.sqlite_connector import query_one
    row = query_one("SELECT empresa_razon_social, empresa_rif FROM config_facturadigital WHERE id=1")
    return {"empresa_razon_social": row["empresa_razon_social"] if row else "",
            "empresa_rif": row["empresa_rif"] if row else ""}


class SendRequest(BaseModel):
    telefono: str
    mensaje: str = ""
    archivo_nombre: str = ""
    archivo_base64: str = ""
    archivo_mimetype: str = ""


def _get_whatsapp_url(path: str) -> str:
    return f"{settings.whatsapp_service_url}{path}"


@router.get("/status")
def whatsapp_status():
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(_get_whatsapp_url("/api/status"))
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "WhatsApp service not available")


@router.get("/qr")
def get_qr():
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(_get_whatsapp_url("/api/qr"))
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "WhatsApp service not available")


@router.post("/send")
def send_message(body: SendRequest):
    try:
        cfg = _load_empresa_config()
        msg = body.mensaje
        msg = msg.replace("{empresa_razon_social}", cfg.get("empresa_razon_social", ""))
        msg = msg.replace("{empresa_rif}", cfg.get("empresa_rif", ""))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            msg = msg.replace("{" + k + "}", v)
        payload = {
            "telefono": body.telefono,
            "mensaje": msg,
        }
        if body.archivo_base64 and body.archivo_nombre:
            payload["archivo_base64"] = body.archivo_base64
            payload["archivo_nombre"] = body.archivo_nombre
            payload["archivo_mimetype"] = body.archivo_mimetype or "application/octet-stream"

        with httpx.Client(timeout=300) as client:
            resp = client.post(_get_whatsapp_url("/api/send"), json=payload)
            if resp.status_code >= 400:
                data = resp.json()
                raise HTTPException(resp.status_code, data.get("error", "Error en el servicio WhatsApp"))
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "WhatsApp service not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/logout")
def logout():
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(_get_whatsapp_url("/api/logout"))
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "WhatsApp service not available")
