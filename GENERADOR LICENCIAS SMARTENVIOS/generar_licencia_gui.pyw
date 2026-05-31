import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, sys, json, subprocess, hashlib
from datetime import date, timedelta
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

BASE = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY = os.path.join(BASE, "private.pem")
PUBLIC_KEY = os.path.join(BASE, "public.pem")


def generar_machine_code_local():
    parts = []
    try:
        r = subprocess.run("wmic csproduct get uuid", shell=True, capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line and line != "UUID" and not line.startswith("wmic"):
                parts.append(hashlib.md5(line.encode()).hexdigest()[:8])
                break
    except:
        pass
    try:
        r = subprocess.run("wmic diskdrive get serialnumber", shell=True, capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line and line != "SerialNumber" and not line.startswith("wmic"):
                parts.append(hashlib.md5(line.encode()).hexdigest()[:8])
                break
    except:
        pass
    return "-".join(parts[:2]) if parts else "UNKNOWN"


def generar_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(PRIVATE_KEY, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(PUBLIC_KEY, "wb") as f:
        f.write(key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
    return True


def crear_licencia(machine, issued_str, expiry_str, lic_path):
    with open(PRIVATE_KEY, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)
    data = {"machine": machine, "issued": issued_str, "expiry": expiry_str}
    msg = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    sig = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    data["sig"] = sig.hex()
    with open(lic_path, "w") as f:
        json.dump(data, f, indent=2)
    return data


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generar Licencia - SmartEnvio")
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 460) // 2
        self.geometry(f"520x460+{x}+{y}")

        self._build_ui()
        self._check_keys()

    def _build_ui(self):
        f = tk.Frame(self, bg="#f8fafc", padx=25, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Generador de Licencias", font=("Segoe UI", 16, "bold"),
                 fg="#16a34a", bg="#f8fafc").pack(anchor="w")
        tk.Label(f, text="SmartEnvio", font=("Segoe UI", 9),
                 fg="#94a3b8", bg="#f8fafc").pack(anchor="w", pady=(0, 12))

        # Machine code (editable)
        tk.Label(f, text="Codigo del equipo DESTINO:", font=("Segoe UI", 9, "bold"),
                 fg="#334155", bg="#f8fafc").pack(anchor="w")
        frm_mc = tk.Frame(f, bg="#f8fafc")
        frm_mc.pack(fill="x", pady=(2, 10))
        self.entry_machine = tk.Entry(frm_mc, font=("Consolas", 10), bd=1, relief="solid")
        self.entry_machine.pack(side="left", fill="x", expand=True)
        self.entry_machine.insert(0, generar_machine_code_local())
        self.entry_machine.focus_set()

        def ctx_pegar():
            import subprocess, tempfile
            try:
                p = os.path.join(tempfile.gettempdir(), "_smartpaste.txt")
                subprocess.run(f"powershell -command \"Get-Clipboard | Out-File -Encoding utf8 '{p}'\"", shell=True, capture_output=True, timeout=5)
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        txt = f.read().strip()
                    if txt:
                        txt = txt.strip().lstrip("\ufeff").lstrip("\uFEFF")
                        self.entry_machine.delete(0, tk.END)
                        self.entry_machine.insert(0, txt)
            except:
                pass
        def ctx_copiar():
            txt = self.entry_machine.get()
            if txt:
                import subprocess, tempfile
                p = os.path.join(tempfile.gettempdir(), "_smartcopy.txt")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(txt)
                subprocess.run(f"type \"{p}\" | clip", shell=True, capture_output=True)
        menu_ctx = tk.Menu(self, tearoff=0)
        menu_ctx.add_command(label="Pegar", command=ctx_pegar)
        menu_ctx.add_command(label="Copiar", command=ctx_copiar)
        def mostrar_ctx(e):
            menu_ctx.tk_popup(e.x_root, e.y_root)
        self.entry_machine.bind("<Button-3>", mostrar_ctx)

        btn_local = tk.Button(frm_mc, text="mi PC", font=("Segoe UI", 8),
                               bg="#e2e8f0", fg="#334155", padx=6, pady=2,
                               relief="flat", cursor="hand2",
                               command=lambda: self.entry_machine.delete(0, tk.END) or self.entry_machine.insert(0, generar_machine_code_local()))
        btn_local.pack(side="right", padx=(4, 0))

        # Mode
        mode_frame = tk.Frame(f, bg="#f8fafc")
        mode_frame.pack(fill="x", pady=(0, 8))
        self.mode_var = tk.StringVar(value="dias")
        tk.Radiobutton(mode_frame, text="Por dias", variable=self.mode_var, value="dias",
                       command=self._toggle_mode, bg="#f8fafc", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        tk.Radiobutton(mode_frame, text="Fechas exactas", variable=self.mode_var, value="fechas",
                       command=self._toggle_mode, bg="#f8fafc", font=("Segoe UI", 9)).pack(side="left")

        # Dias mode
        self.dias_frame = tk.Frame(f, bg="#f8fafc")
        self.dias_frame.pack(fill="x", pady=(0, 8))
        tk.Label(self.dias_frame, text="Duracion (dias):", font=("Segoe UI", 9),
                 fg="#334155", bg="#f8fafc").pack(anchor="w")
        self.entry_dias = tk.Entry(self.dias_frame, font=("Segoe UI", 11), width=10)
        self.entry_dias.pack(anchor="w", pady=(2, 0))
        self.entry_dias.insert(0, "30")

        # Fechas mode
        self.fechas_frame = tk.Frame(f, bg="#f8fafc")
        tk.Label(self.fechas_frame, text="Inicio (YYYY-MM-DD):", font=("Segoe UI", 9),
                 fg="#334155", bg="#f8fafc").pack(anchor="w")
        self.entry_issued = tk.Entry(self.fechas_frame, font=("Segoe UI", 11), width=16)
        self.entry_issued.pack(anchor="w", pady=(2, 4))
        self.entry_issued.insert(0, date.today().isoformat())
        tk.Label(self.fechas_frame, text="Fin (YYYY-MM-DD):", font=("Segoe UI", 9),
                 fg="#334155", bg="#f8fafc").pack(anchor="w")
        self.entry_expiry = tk.Entry(self.fechas_frame, font=("Segoe UI", 11), width=16)
        self.entry_expiry.pack(anchor="w", pady=(2, 0))
        self.fechas_frame.pack_forget()
        self._toggle_mode()

        # Status
        self.lbl_status = tk.Label(f, text="", font=("Segoe UI", 9), fg="#16a34a", bg="#f8fafc")
        self.lbl_status.pack(anchor="w", pady=(8, 2))

        # Buttons
        btn_frame = tk.Frame(f, bg="#f8fafc")
        btn_frame.pack(fill="x", pady=(8, 0))
        self.btn_generar = tk.Button(btn_frame, text="Generar licencia",
                                      font=("Segoe UI", 10, "bold"), bg="#16a34a", fg="white",
                                      padx=20, pady=6, relief="flat", cursor="hand2",
                                      command=self._generar)
        self.btn_generar.pack(side="left", padx=(0, 8))
        self.btn_cerrar = tk.Button(btn_frame, text="Cerrar",
                                     font=("Segoe UI", 9), bg="#f1f5f9", fg="#64748b",
                                     padx=14, pady=6, relief="flat", cursor="hand2",
                                     command=self.destroy)
        self.btn_cerrar.pack(side="right")

    def _toggle_mode(self):
        if self.mode_var.get() == "dias":
            self.dias_frame.pack(fill="x", pady=(0, 8))
            self.fechas_frame.pack_forget()
        else:
            self.dias_frame.pack_forget()
            self.fechas_frame.pack(fill="x", pady=(0, 8))

    def _check_keys(self):
        if not os.path.exists(PRIVATE_KEY):
            self.lbl_status.config(text="No hay llaves RSA. Haz clic en 'Generar llaves RSA'.", fg="#dc2626")

    def _gen_keys(self):
        try:
            generar_keypair()
            self.lbl_status.config(text="OK - Llaves RSA generadas.", fg="#16a34a")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar llaves:\n{e}")

    def _generar(self):
        if not os.path.exists(PRIVATE_KEY):
            self._gen_keys()
            if not os.path.exists(PRIVATE_KEY):
                messagebox.showerror("Error", "No se pudieron generar las llaves RSA.")
                return

        machine = self.entry_machine.get().strip().lstrip("\ufeff").lstrip("\uFEFF")
        if not machine:
            messagebox.showerror("Error", "Escribe el codigo del equipo destino.")
            return

        try:
            if self.mode_var.get() == "dias":
                d = int(self.entry_dias.get())
                if d <= 0: raise ValueError
                issued = date.today().isoformat()
                expiry = (date.today() + timedelta(days=d)).isoformat()
            else:
                issued = self.entry_issued.get().strip()
                expiry = self.entry_expiry.get().strip()
                date.fromisoformat(issued)
                date.fromisoformat(expiry)
        except ValueError:
            messagebox.showerror("Error", "Fechas invalidas. Usa formato YYYY-MM-DD.")
            return

        lic_path = filedialog.asksaveasfilename(
            title="Guardar licencia como",
            defaultextension=".lic",
            filetypes=[("License files", "*.lic")],
            initialfile="license.lic")
        if not lic_path:
            return

        try:
            data = crear_licencia(machine, issued, expiry, lic_path)
            self.lbl_status.config(text=f"OK - Licencia guardada", fg="#16a34a")
            msg = (f"Licencia generada\n\n"
                   f"Equipo: {machine}\n"
                   f"Inicio: {data['issued']}\n"
                   f"Fin:    {data['expiry']}\n\n"
                   f"Archivo: {lic_path}")
            messagebox.showinfo("Licencia generada", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar licencia:\n{e}")

if __name__ == "__main__":
    App().mainloop()
