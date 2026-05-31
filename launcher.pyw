import tkinter as tk
from tkinter import ttk
import subprocess, threading, os, time, sys, tempfile, re, json

BASE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(tempfile.gettempdir(), "smartenvio.lock")
procs = []
tray_icon = None
watchdog_active = True  # set False after user-requested shutdown

if os.path.exists(LOCK):
    try:
        old_pid = int(open(LOCK).read().strip())
        alive = subprocess.run(f"tasklist /fi \"PID eq {old_pid}\"", shell=True,
                               capture_output=True, text=True)
        if str(old_pid) in alive.stdout:
            subprocess.run(f"taskkill /pid {old_pid} /f >nul 2>nul", shell=True)
            time.sleep(0.5)
            subprocess.Popen("start http://localhost:5173", shell=True)
            sys.exit(0)
    except:
        pass
    try: os.remove(LOCK)
    except: pass

open(LOCK, "w").write(str(os.getpid()))

def ensure_dep(name):
    for _ in range(2):
        try:
            __import__(name)
            return True
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", name, "-q"],
                                      timeout=120)
                continue
            except Exception:
                try:
                    subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
                    subprocess.check_call([sys.executable, "-m", "pip", "install", name, "-q"],
                                          timeout=120)
                except Exception:
                    pass
    return False

if not ensure_dep("pystray") or not ensure_dep("PIL"):
    root = tk.Tk()
    root.withdraw()
    tk.messagebox.showerror("SmartEnvios - Error",
        "No se pudieron instalar las dependencias necesarias (pystray, Pillow).\n\n"
        "Asegúrese de tener conexión a Internet o instale manualmente:\n"
        f'"{sys.executable}" -m pip install pystray Pillow')
    sys.exit(1)

import pystray
from PIL import Image, ImageDraw, ImageTk

def bezier(t, p0, p1, p2):
    return (1-t)**2 * p0 + 2*(1-t)*t * p1 + t**2 * p2

def crear_logo(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.rounded_rectangle([2, 2, s-2, s-2], radius=s//4, fill="#16a34a")
    # S-curve matching sidebar SVG: M20 20 Q44 8 44 28 Q20 28 20 44 Q44 54 44 44
    segs = [
        ((20,20), (44,8),  (44,28)),
        ((44,28), (20,28), (20,44)),
        ((20,44), (44,54), (44,44)),
    ]
    w = max(3, s // 11)
    for p0, p1, p2 in segs:
        pts = [(bezier(t/60, p0[0], p1[0], p2[0]) * s/64,
                bezier(t/60, p0[1], p1[1], p2[1]) * s/64)
               for t in range(61)]
        for i in range(len(pts)-1):
            d.line([pts[i], pts[i+1]], fill="white", width=w)
    return img

crear_imagen_tray = crear_logo

# Save logo PNG for favicon etc.
crear_logo(128).save(os.path.join(BASE, "frontend", "dist", "logo.png"))

def log(msg):
    status_var.set(msg)
    root.update_idletasks()

def run(cmd, cwd=None, shell=True, env=None):
    si = subprocess.STARTUPINFO()
    si.dwFlags |= 1  # STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    p = subprocess.Popen(cmd, cwd=cwd or BASE, shell=shell, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW,
                         startupinfo=si)
    procs.append(p)
    return p

def puertos_en_uso():
    r = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True)
    pids = set()
    for line in r.stdout.splitlines():
        if "LISTENING" in line and any(f":{p}" in line for p in ["8000","3001","5173"]):
            parts = line.strip().split()
            if len(parts) >= 5:
                try: pids.add(int(parts[-1]))
                except: pass
    return pids

def kill_by_port():
    for pid in puertos_en_uso():
        subprocess.run(f"taskkill /pid {pid} /f >nul 2>nul", shell=True)

def task():
    step(0, "Cerrando servicios anteriores...")
    kill_by_port()
    time.sleep(1.5)

    # Generar machine code (UUID + Serial de disco)
    step(1, "Generando identificador del equipo...")
    import hashlib
    parts = []
    for cmd, filtro in [("wmic csproduct get uuid", "UUID"),
                         ("wmic diskdrive get serialnumber", "SerialNumber")]:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            for ln in r.stdout.splitlines():
                ln_val = ln.strip().strip('\ufeff').strip('\uFEFF')
                if ln_val and ln_val != filtro and not ln_val.startswith("wmic"):
                    parts.append(hashlib.md5(ln_val.encode()).hexdigest()[:8])
                    break
        except:
            pass
    mc_launcher = "-".join(parts[:2]) if parts else ""

    # Validar licencia desde el launcher (sin backend)
    lic_valida = False
    razon = ""
    from datetime import date
    # Asegurar que cryptography esta instalado
    try:
        __import__("cryptography")
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography", "-q"],
                                  timeout=120)
        except:
            pass
    lic_file = os.path.join(BASE, "license.lic")
    if not os.path.exists(lic_file):
        razon = "Sin archivo de licencia"
    else:
        try:
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import serialization, hashes
            with open(lic_file) as f:
                lic = json.load(f)
            machine_raw = lic.get("machine", "")
            issued = lic.get("issued", "")
            expiry = lic.get("expiry", "")
            sig = lic.get("sig", "")
            if not sig:
                razon = "Licencia sin firma"
            else:
                pub_pem = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmvSLMt3dRUYRqmsab963
ESlYEe83UtEupVsG2fME+gozuvnhdiK0fDN7KoGHQqTAVCbBkL5PBmBjpHBzfM63
nVfPDa8tSQiL2RvZKKt1iBiOiDtoy6qMSjsITxBCeo2VZSMIMse4w/ipjlI4NRt6
okim3lEvZv/zn/supSdXSVniw3YFikYG4jDpwB4MEYVUM71npK89V+HVy0TTZ/Bd
HB0bB4/A3CNlOsb9t3MCv6RFpBdwdzvMUnNTLsGRk0nFavcA1MerwW6YIY7KwHkw
U6bsKrFq8JGE4fXGQ1GHVoDhuSSK56Rry/K3POljqIaJSwCl3PrZQ2675R4zFq56
GQIDAQAB
-----END PUBLIC KEY-----"""
                public_key = serialization.load_pem_public_key(pub_pem.encode())
                msg = json.dumps({"machine": machine_raw, "issued": issued, "expiry": expiry},
                                 sort_keys=True, separators=(",", ":")).encode()
                try:
                    public_key.verify(bytes.fromhex(sig), msg, padding.PKCS1v15(), hashes.SHA256())
                    machine = machine_raw.strip().lstrip("\ufeff").lstrip("\uFEFF")
                    if not mc_launcher:
                        razon = "No se pudo generar codigo de maquina"
                    elif machine != mc_launcher:
                        razon = "Esta licencia no corresponde a este equipo"
                    elif expiry and date.fromisoformat(expiry) < date.today():
                        razon = "Licencia vencida"
                    else:
                        lic_valida = True
                        razon = "OK"
                except Exception:
                    razon = "Firma invalida"
        except Exception as e:
            razon = f"Error al leer licencia: {e}"

    print(f"DEBUG launcher: valida={lic_valida} razon={razon} machine={mc_launcher}")

    if not lic_valida:
        kill_by_port()
        progress["value"] = 100
        print("DEBUG launcher: mc_launcher:", repr(mc_launcher), "razon:", repr(razon))
        root.after(0, lambda: mostrar_sin_licencia(mc_launcher or "(no detectado)", razon))
        return

    # Licencia valida: arrancar backend y demas servicios
    step(2, "Iniciando Backend (puerto 8000)...")
    run(f'"{sys.executable}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000',
        cwd=os.path.join(BASE, "backend"))
    for i in range(15):
        time.sleep(1)
        if puerto_activo(8000): break

    step(3, "Verificando dependencias...")
    env_npm = os.environ.copy()
    env_npm["PUPPETEER_SKIP_CHROMIUM_DOWNLOAD"] = "true"
    if not os.path.exists(os.path.join(BASE, "frontend", "node_modules")):
        log("Instalando dependencias del frontend...")
        p = run("npm install", cwd=os.path.join(BASE, "frontend"), env=env_npm)
        if p: p.wait()
    if not os.path.exists(os.path.join(BASE, "whatsapp-service", "node_modules")):
        log("Instalando dependencias de WhatsApp...")
        p = run("npm install", cwd=os.path.join(BASE, "whatsapp-service"), env=env_npm)
        if p: p.wait()

    step(4, "Iniciando WhatsApp Service (puerto 3001)...")
    run("node index.js", cwd=os.path.join(BASE, "whatsapp-service"))
    time.sleep(2)

    step(5, "Iniciando Frontend (puerto 5173)...")
    p_f = subprocess.Popen(
        ["node", "node_modules/vite/bin/vite.js", "dev", "--host", "--port", "5173"],
        cwd=os.path.join(BASE, "frontend"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    procs.append(p_f)
    time.sleep(2)

    step(6, "Abriendo navegador...")
    subprocess.Popen("start http://localhost:5173", shell=True)
    time.sleep(0.5)

    progress["value"] = 100
    status_var.set("Todos los servicios iniciados")
    root.after(500, mostrar_tray)
    threading.Thread(target=watchdog, daemon=True).start()


def puerto_activo(puerto):
    r = subprocess.run("netstat -ano", shell=True, capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "LISTENING" in line and f":{puerto}" in line:
            return True
    return False


def watchdog():
    servicios = {"8000": "Backend", "3001": "WhatsApp", "5173": "Frontend"}
    while watchdog_active:
        time.sleep(10)
        for puerto, nombre in servicios.items():
            if not puerto_activo(puerto) and watchdog_active:
                log(f"⚠ {nombre} caído, reiniciando...")
                if puerto == "8000":
                    si2 = subprocess.STARTUPINFO()
                    si2.dwFlags |= 1
                    si2.wShowWindow = 0
                    p2 = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                        cwd=os.path.join(BASE, "backend"),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW, text=True,
                        startupinfo=si2)
                    procs.append(p2)
                    def _leer2(p=p2):
                        for ln in p.stdout or []: print("BACKEND:", ln.rstrip())
                    threading.Thread(target=_leer2, daemon=True).start()
                elif puerto == "3001":
                    run("node index.js", cwd=os.path.join(BASE, "whatsapp-service"))
                elif puerto == "5173":
                    pf2 = subprocess.Popen(
                        ["node", "node_modules/vite/bin/vite.js", "dev", "--host", "--port", "5173"],
                        cwd=os.path.join(BASE, "frontend"),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    procs.append(pf2)
                time.sleep(5)
                if puerto_activo(puerto):
                    log(f"✅ {nombre} reiniciado")
                else:
                    log(f"❌ {nombre} no pudo reiniciarse")

def mostrar_sin_licencia(maquina, razon=""):
    root.geometry("560x360")
    for w in frame.winfo_children():
        w.destroy()
    status_var.set("Sin licencia valida")

    tk.Label(frame, text="SmartEnvios", font=("Segoe UI", 18, "bold"),
             fg="#16a34a", bg="#f8fafc", anchor="center").pack(pady=(10, 2))
    tk.Label(frame, text="No hay licencia valida", font=("Segoe UI", 11, "bold"),
             fg="#dc2626", bg="#f8fafc", anchor="center").pack(pady=(4, 8))

    if razon:
        tk.Label(frame, text=f"Motivo: {razon}", font=("Segoe UI", 9, "bold"),
                 fg="#dc2626", bg="#f8fafc", anchor="center").pack(pady=(0, 6))
    else:
        tk.Label(frame, text="Motivo: (desconocido)", font=("Segoe UI", 9),
                 fg="#94a3b8", bg="#f8fafc", anchor="center").pack(pady=(0, 6))

    tk.Label(frame, text="Debes generar una licencia para este equipo:",
             font=("Segoe UI", 9), fg="#334155", bg="#f8fafc", anchor="center").pack()

    mc_text = tk.Text(frame, height=1, width=30, font=("Consolas", 14, "bold"),
                      bg="#fff", fg="#991b1b", relief="solid", bd=2,
                      padx=6, pady=4, cursor="xterm")
    mc_text.insert("1.0", maquina or "(no detectado)")
    mc_text.pack(pady=(6, 6))
    mc_text.tag_add(tk.SEL, "1.0", "end-1c")
    mc_text.mark_set(tk.INSERT, "1.0")
    mc_text.focus_set()
    menu_context = tk.Menu(root, tearoff=0)
    menu_context.add_command(label="Copiar", font=("Segoe UI", 9),
                             command=lambda: copiar_codigo())
    menu_context.add_command(label="Seleccionar todo", font=("Segoe UI", 9),
                             command=lambda: (mc_text.tag_add(tk.SEL, "1.0", "end-1c"), mc_text.mark_set(tk.INSERT, "1.0")))
    def mostrar_menu(e):
        menu_context.tk_popup(e.x_root, e.y_root)
    mc_text.bind("<Button-3>", mostrar_menu)

    def copiar_codigo():
        txt = maquina or ""
        if txt:
            import subprocess, tempfile
            p = os.path.join(tempfile.gettempdir(), "smartenvio_codigo.txt")
            with open(p, "w") as f:
                f.write(txt)
            subprocess.run(f"type \"{p}\" | clip", shell=True, capture_output=True)
    def copiar_por_tecla(e):
        copiar_codigo()
        return "break"
    mc_text.bind("<Control-Key-c>", copiar_por_tecla)
    mc_text.bind("<Control-Key-C>", copiar_por_tecla)

    tk.Label(frame, text="Envie este codigo al administrador.",
             font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc", anchor="center").pack()
    tk.Label(frame, text="Cuando reciba license.lic, copielo en la carpeta raiz",
             font=("Segoe UI", 8), fg="#94a3b8", bg="#f8fafc", anchor="center").pack()

    btn_cerrar = tk.Button(frame, text="Cerrar", command=salir,
                           font=("Segoe UI", 9), bg="#dc2626", fg="white",
                           relief="flat", padx=20, pady=5, cursor="hand2")
    btn_cerrar.pack(pady=(12, 0))

def step(n, msg):
    progress["value"] = (n / 5) * 100
    log(msg)
    time.sleep(0.3)

def salir():
    global tray_icon, watchdog_active
    watchdog_active = False
    if tray_icon:
        tray_icon.stop()
        tray_icon = None
    for p in procs:
        try: p.kill()
        except: pass
    kill_by_port()
    try: os.remove(LOCK)
    except: pass
    root.destroy()
    os._exit(0)

def mostrar_tray():
    global tray_icon
    root.withdraw()
    menu = pystray.Menu(
        pystray.MenuItem("Cerrar SmartEnvios", lambda: root.after(0, salir))
    )
    tray_icon = pystray.Icon("smartenvio", crear_imagen_tray(), "SmartEnvios", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

root = tk.Tk()
root.title("SmartEnvios - Iniciando servicios")
root.resizable(False, False)
root.configure(bg="#f8fafc")
x = (root.winfo_screenwidth() - 480) // 2
y = (root.winfo_screenheight() - 220) // 2
root.geometry(f"480x220+{x}+{y}")
root.lift()
root.attributes("-topmost", True)
root.focus_force()
root.after(1000, lambda: root.attributes("-topmost", False))

try:
    from ctypes import windll
    windll.shell32.SetCurrentProcessExplicitAppUserModelID("smartenvio.launcher")
except:
    pass

frame = tk.Frame(root, bg="#f8fafc", padx=30, pady=25)
frame.pack(fill="both", expand=True)

header = tk.Frame(frame, bg="#f8fafc")
header.pack(fill="x", anchor="w")
root.logo_tk = ImageTk.PhotoImage(crear_logo(64))
tk.Label(header, image=root.logo_tk, bg="#f8fafc").pack(side="left", padx=(0, 12))

tk.Label(header, text="SmartEnvios", font=("Segoe UI", 18, "bold"),
         fg="#16a34a", bg="#f8fafc").pack(side="left")

tk.Label(frame, text="Iniciando servicios...", font=("Segoe UI", 10),
         fg="#64748b", bg="#f8fafc").pack(anchor="w", pady=(2, 12))

progress = ttk.Progressbar(frame, length=420, mode="determinate", value=0)
progress.pack(pady=(0, 10))

status_var = tk.StringVar(value="Preparando...")
lbl_status = tk.Label(frame, textvariable=status_var, font=("Segoe UI", 9),
                      fg="#334155", bg="#f8fafc", wraplength=420, anchor="w", justify="left")
lbl_status.pack(fill="x")

btn_exit = tk.Button(frame, text="Cancelar", command=salir,
                     font=("Segoe UI", 9), bg="#e2e8f0", fg="#334155",
                     relief="flat", padx=16, pady=4, cursor="hand2")
btn_exit.pack(anchor="e", pady=(10, 0))

threading.Thread(target=task, daemon=True).start()
root.mainloop()
