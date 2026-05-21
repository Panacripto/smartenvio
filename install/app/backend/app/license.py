import os, json, subprocess, hashlib

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LICENSE_FILE = os.path.join(ROOT, "license.lic")

# Llave publica RSA embebida (NO puede firmar, solo verificar)
_PUBLIC_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmvSLMt3dRUYRqmsab963
ESlYEe83UtEupVsG2fME+gozuvnhdiK0fDN7KoGHQqTAVCbBkL5PBmBjpHBzfM63
nVfPDa8tSQiL2RvZKKt1iBiOiDtoy6qMSjsITxBCeo2VZSMIMse4w/ipjlI4NRt6
okim3lEvZv/zn/supSdXSVniw3YFikYG4jDpwB4MEYVUM71npK89V+HVy0TTZ/Bd
HB0bB4/A3CNlOsb9t3MCv6RFpBdwdzvMUnNTLsGRk0nFavcA1MerwW6YIY7KwHkw
U6bsKrFq8JGE4fXGQ1GHVoDhuSSK56Rry/K3POljqIaJSwCl3PrZQ2675R4zFq56
GQIDAQAB
-----END PUBLIC KEY-----"""


def _generar_machine_code() -> str:
    for cmd in ["powershell -Command \"(Get-CimInstance Win32_ComputerSystemProduct).UUID\"",
                "powershell -Command \"(Get-WmiObject Win32_ComputerSystemProduct).UUID\"",
                "wmic csproduct get uuid"]:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            for ln in r.stdout.splitlines():
                ln = ln.strip().strip('\ufeff').strip('\uFEFF')
                if ln and ln != "UUID" and not ln.startswith("wmic"):
                    return hashlib.md5(ln.encode()).hexdigest()[:8]
        except:
            pass
    return "UNKNOWN"


def _verificar_firma(data: dict, firma_hex: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(_PUBLIC_PEM.encode())
        msg = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        sig = bytes.fromhex(firma_hex)
        public_key.verify(sig, msg, padding.PKCS1v15(), hashes.SHA256())
        return True
    except:
        return False


def verificar_licencia() -> dict:
    if not os.path.exists(LICENSE_FILE):
        return {"valida": False, "razon": "Sin archivo de licencia"}
    try:
        with open(LICENSE_FILE) as f:
            lic = json.load(f)
        machine_raw = lic.get("machine", "")
        issued = lic.get("issued", "")
        expiry = lic.get("expiry", "")
        sig = lic.get("sig", "")
        if not sig:
            return {"valida": False, "razon": "Licencia sin firma"}
        # Verificar firma usando el machine code original (puede tener BOM)
        data = {"machine": machine_raw, "issued": issued, "expiry": expiry}
        if not _verificar_firma(data, sig):
            # Reintentar sin BOM (por si se genero sin BOM)
            data_clean = {"machine": machine_raw.strip().lstrip("\ufeff").lstrip("\uFEFF"), "issued": issued, "expiry": expiry}
            if not _verificar_firma(data_clean, sig):
                return {"valida": False, "razon": "Firma invalida"}
        machine = machine_raw.strip().lstrip("\ufeff").lstrip("\uFEFF")
        from datetime import date
        if expiry and date.fromisoformat(expiry) < date.today():
            return {"valida": False, "razon": "Licencia vencida"}
        mc = _generar_machine_code()
        if machine != mc:
            return {"valida": False, "razon": "Esta licencia no corresponde a este equipo", "machine_code_actual": mc, "machine_code_lic": machine}
        return {"valida": True, "razon": "OK", "expiry": expiry}
    except Exception as e:
        return {"valida": False, "razon": f"Error al leer licencia: {e}"}


def estado_licencia() -> dict:
    result = verificar_licencia()
    mc = _generar_machine_code()
    result["machine_code"] = mc if not result.get("valida") else ""
    return result


def licencia_activa() -> bool:
    if not os.path.exists(LICENSE_FILE):
        return False
    lic = verificar_licencia()
    return lic.get("valida", False)
