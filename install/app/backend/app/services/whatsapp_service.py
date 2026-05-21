import httpx
from typing import Optional

from app.config import settings


def enviar_mensaje_whatsapp(telefono: str, mensaje: str) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{settings.whatsapp_service_url}/api/send",
                json={"telefono": telefono, "mensaje": mensaje},
            )
            if resp.status_code == 200:
                return {"success": True}
            else:
                return {"success": False, "error": resp.text}
    except httpx.ConnectError:
        return {"success": False, "error": "WhatsApp service not available"}
    except Exception as e:
        return {"success": False, "error": str(e)}
