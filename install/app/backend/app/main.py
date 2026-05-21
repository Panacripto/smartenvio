import os, subprocess, threading, time, json, tempfile
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database.sqlite_connector import init_db
from app.api import clientes, ventas, compras, inventario, cuentas, mensajes, plantillas, programaciones, whatsapp, odbc, dashboard, cobranza, smartenvio, facturadigital, campaigns
from app.license import licencia_activa, estado_licencia


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="DEV MENSAJERIA - Plataforma de Mensajería WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)


@app.middleware("http")
async def license_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/api/license/status", "/api/license/activate", "/api/services/status", "/api/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    if not licencia_activa():
        lic = estado_licencia()
        return JSONResponse(status_code=403, content={"error": "Licencia invalida", "license": lic})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(clientes.router, prefix="/api/clientes", tags=["Clientes"])
app.include_router(ventas.router, prefix="/api/ventas", tags=["Ventas"])
app.include_router(compras.router, prefix="/api/compras", tags=["Compras"])
app.include_router(inventario.router, prefix="/api/inventario", tags=["Inventario"])
app.include_router(cuentas.router, prefix="/api/cuentas", tags=["Cuentas"])
app.include_router(mensajes.router, prefix="/api/mensajes", tags=["Mensajes"])
app.include_router(plantillas.router, prefix="/api/plantillas", tags=["Plantillas"])
app.include_router(programaciones.router, prefix="/api/programaciones", tags=["Programaciones"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(odbc.router, prefix="/api/odbc", tags=["ODBC"])
app.include_router(cobranza.router, prefix="/api/cobranza", tags=["Cobranza"])
app.include_router(smartenvio.router, prefix="/api/smartenvio", tags=["SmartEnvios"])
app.include_router(facturadigital.router, prefix="/api/factura-digital", tags=["Factura Digital"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campañas"])


@app.get("/api/health")
def health():
    if not licencia_activa():
        return JSONResponse(status_code=403, content={"error": "Licencia invalida"})
    return {"status": "ok"}


@app.get("/api/license/status")
def license_status():
    return estado_licencia()

LOCK_FILE = os.path.join(tempfile.gettempdir(), "smartenvio.lock")

@app.post("/api/shutdown")
def shutdown():
    def _kill():
        time.sleep(0.5)

        # Kill launcher (read PID from lock file)
        try:
            if os.path.exists(LOCK_FILE):
                with open(LOCK_FILE) as f:
                    pid = int(f.read().strip())
                subprocess.run(f"taskkill /pid {pid} /f >nul 2>nul", shell=True)
                try: os.remove(LOCK_FILE)
                except: pass
        except:
            pass

        # Kill WhatsApp and frontend by port
        try:
            r = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if "LISTENING" in line and any(f":{p}" in line for p in ["3001", "5173"]):
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            pid = int(parts[-1])
                            subprocess.run(f"taskkill /pid {pid} /f >nul 2>nul", shell=True)
                        except:
                            pass
        except:
            pass
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return {"ok": True}


FOOTER_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "footer_config.json")


def _leer_footer() -> str:
    try:
        with open(FOOTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("texto", "")
    except:
        return ""


def _guardar_footer(texto: str):
    with open(FOOTER_FILE, "w", encoding="utf-8") as f:
        json.dump({"texto": texto}, f, ensure_ascii=False)


@app.get("/api/config/footer")
def get_footer():
    return {"texto": _leer_footer()}


@app.put("/api/config/footer")
def set_footer(body: dict):
    texto = body.get("texto", "")
    _guardar_footer(texto)
    return {"ok": True}


@app.get("/api/services/status")
def services_status():
    wa_status = "stopped"
    wa_connected = False
    try:
        r = httpx.get("http://127.0.0.1:3001/api/status", timeout=3)
        if r.status_code == 200:
            data = r.json()
            wa_status = data.get("status", "unknown")
            wa_connected = data.get("status") == "connected"
        else:
            wa_status = "error"
    except:
        wa_status = "stopped"
    return {
        "backend": "running",
        "whatsapp": {"status": wa_status, "connected": wa_connected},
    }
