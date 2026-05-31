import os, subprocess, threading, time, json, tempfile
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database.sqlite_connector import init_db
from app.api import clientes, ventas, compras, inventario, cuentas, mensajes, plantillas, programaciones, whatsapp, odbc, dashboard, cobranza, smartenvio, facturadigital, campaigns, contactos, contactos_google, gestionpagos, rates
from app.license import licencia_activa, estado_licencia


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        gestionpagos._sync_desde_odbc()
    except Exception:
        pass
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
    if path in ("/api/license/status", "/api/license/activate", "/api/services/status", "/api/network/info", "/api/health", "/docs", "/openapi.json", "/redoc"):
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
app.include_router(contactos.router, prefix="/api/contactos", tags=["Contactos"])
app.include_router(contactos_google.router, prefix="/api/contactos", tags=["Contactos Google"])
app.include_router(gestionpagos.router, prefix="/api/gestion-pagos", tags=["Gestión de Pagos"])
app.include_router(rates.router, prefix="/api/rates", tags=["Indicadores"])


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


def _leer_footer() -> str:
    from app.database.sqlite_connector import query_one
    row = query_one("SELECT texto FROM config_footer WHERE id=1")
    return row["texto"] if row else ""


def _guardar_footer(texto: str):
    from app.database.sqlite_connector import execute
    execute("UPDATE config_footer SET texto=?", (texto,))


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
    wa_phone = None
    try:
        r = httpx.get("http://127.0.0.1:3001/api/status", timeout=3)
        if r.status_code == 200:
            data = r.json()
            wa_status = data.get("status", "unknown")
            wa_connected = data.get("status") == "connected"
            wa_phone = data.get("phone")
        else:
            wa_status = "error"
    except:
        wa_status = "stopped"
    return {
        "backend": "running",
        "whatsapp": {"status": wa_status, "connected": wa_connected, "phone": wa_phone},
    }


@app.post("/api/preview")
def preview_template(body: dict):
    tipo = body.get("tipo", "")
    template = body.get("template", "")
    criterio = body.get("criterio", "todas")

    from datetime import date
    hoy = date.today().strftime("%d/%m/%Y")

    if tipo == "gestionpagos":
        from app.database.sqlite_connector import query as sqlq
        from app.api.gestionpagos import _leer_desde_sqlite, _agrupar_por_proveedor, _generar_lista_proveedores, _generar_bloque_todos, _formatear_dias
        rows = _leer_desde_sqlite(criterio)
        if not rows:
            return {"vista": template.replace("{fecha}", hoy).replace("{condicion}", criterio.upper()).replace("{proveedores}", "(sin datos)").replace("{lista_proveedores}", "(sin datos)").replace("{total_general}", "$0.00")}
        proveedores = _agrupar_por_proveedor(rows)
        total_general = sum(p["total"] for p in proveedores)
        total_vencido = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] > 0)
        total_por_vencer = sum(d["monto"] for p in proveedores for d in p["documentos"] if d["dias"] <= 0)
        condicion_map = {"vencidas": "VENCIDAS", "por_vencer": "POR VENCER", "todas": "TODAS"}
        msg = template
        msg = msg.replace("{fecha}", hoy)
        msg = msg.replace("{condicion}", condicion_map.get(criterio, "PENDIENTES"))
        msg = msg.replace("{proveedores}", _generar_bloque_todos(proveedores))
        msg = msg.replace("{lista_proveedores}", _generar_lista_proveedores(proveedores))
        msg = msg.replace("{proveedor}", proveedores[0]["nombre"])
        msg = msg.replace("{codigo}", proveedores[0]["codigo"])
        msg = msg.replace("{total_proveedor}", f"${proveedores[0]['total']:.2f}")
        msg = msg.replace("{total_vencido}", f"${total_vencido:.2f}")
        msg = msg.replace("{total_por_vencer}", f"${total_por_vencer:.2f}")
        msg = msg.replace("{total_general}", f"${total_general:.2f}")
        return {"vista": msg}

    elif tipo == "smartenvio" or tipo == "cobranza":
        from app.database.odbc_connector import odbc_connector
        dias = body.get("dias", 0)
        sample = {"FC_SALDO_TOTAL": 1500.00, "FC_DOCUMENTOS": 3, "FC_CODIGO": "CLI001", "FC_DESCRIPCION": "Cliente Ejemplo", "FC_TELEFONO": "584121234567"}
        try:
            rows = odbc_connector.query("SELECT FC_CODIGO, FC_DESCRIPCION, FC_TELEFONO FROM Sclientes WHERE FC_TELEFONO IS NOT NULL AND FC_TELEFONO <> ''")
            if rows:
                r = rows[0]
                sample["FC_CODIGO"] = str(r.get("FC_CODIGO", sample["FC_CODIGO"]))
                sample["FC_DESCRIPCION"] = str(r.get("FC_DESCRIPCION", sample["FC_DESCRIPCION"]))
                sample["FC_TELEFONO"] = str(r.get("FC_TELEFONO", sample["FC_TELEFONO"]))
        except:
            pass
        empresa_cfg = {}
        try:
            from app.api.facturadigital import _load_config as _load_fd
            empresa_cfg = _load_fd()
        except: pass
        criterio_txt = "VENCIDAS" if dias < 0 else ("VENCE HOY" if dias == 0 else f"VENCE EN {dias} DÍAS")
        msg = template
        msg = msg.replace("{empresa_razon_social}", empresa_cfg.get("empresa_razon_social", "Mi Empresa"))
        msg = msg.replace("{empresa_rif}", empresa_cfg.get("empresa_rif", "J-12345678-9"))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            msg = msg.replace("{" + k + "}", v)
        msg = msg.replace("{FC_CODIGO}", str(sample.get("FC_CODIGO","CLI001")))
        msg = msg.replace("{FC_DESCRIPCION}", str(sample.get("FC_DESCRIPCION","Cliente Ejemplo")))
        msg = msg.replace("{FC_TELEFONO}", str(sample.get("FC_TELEFONO","584121234567")))
        msg = msg.replace("{FC_SALDO_TOTAL}", f"{float(sample.get('FC_SALDO_TOTAL',1500)):.2f}")
        msg = msg.replace("{FC_DOCUMENTOS}", str(sample.get("FC_DOCUMENTOS",3)))
        msg = msg.replace("{FC_CRITERIO}", criterio_txt)
        return {"vista": msg}

    elif tipo == "facturadigital":
        from app.database.odbc_connector import odbc_connector
        nom = "Cliente Ejemplo"
        try:
            factura = odbc_connector.query("SELECT FC_DESCRIPCION FROM Sclientes WHERE FC_TELEFONO IS NOT NULL AND FC_TELEFONO <> ''")
            if factura:
                nom = str(factura[0].get("FC_DESCRIPCION", nom))
        except:
            pass
        from app.api.facturadigital import _load_config as _load_fd
        cfg = _load_fd()
        msg = template
        msg = msg.replace("{cliente}", nom)
        msg = msg.replace("{facturas}", "DOCUMENTO: FAC-001\nFECHA: HOY\nTOTAL$: 1,500.00\nTASA: 0.00\nTOTAL Bs.: 0.00")
        msg = msg.replace("{empresa_razon_social}", cfg.get("empresa_razon_social", "Mi Empresa"))
        msg = msg.replace("{empresa_rif}", cfg.get("empresa_rif", "J-12345678-9"))
        from app.api.rates import get_rate_vars
        for k, v in get_rate_vars().items():
            msg = msg.replace("{" + k + "}", v)
        return {"vista": msg}

    return {"vista": template}


@app.post("/api/init-data")
def init_data():
    from app.database.sqlite_connector import get_db
    with get_db() as conn:
        conn.executescript("""
            DELETE FROM contactos;
            DELETE FROM campaign_log;
            DELETE FROM campaign_attachments;
            DELETE FROM campaigns;
            DELETE FROM pagos_documentos;
            DELETE FROM pagos_proveedores;
        """)
    return {"ok": True, "mensaje": "Contactos, campañas y proveedores de pago inicializados"}


@app.get("/api/network/info")
def network_info():
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip.startswith("192.") or ip.startswith("10.") or ip.startswith("172."):
                if ip not in ips:
                    ips.append(ip)
    except:
        pass
    return {"ips": ips, "port": 5173}
