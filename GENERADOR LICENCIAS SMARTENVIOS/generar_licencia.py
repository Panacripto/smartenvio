"""
Generador de licencias para SmartEnvio.
Usa RSA asimetrico: la firma se hace con PRIVATE KEY (solo este script),
la verificacion en la app usa PUBLIC KEY (embebida en license.py).

USO:
  python generar_licencia.py --generate-key
  python generar_licencia.py --create --machine CODIGO --issued YYYY-MM-DD --expiry YYYY-MM-DD
  python generar_licencia.py --create --machine CODIGO --dias 365
  python generar_licencia.py --show-machine
"""
import argparse, json, os, subprocess, hashlib
from datetime import date, timedelta

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

BASE = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY = os.path.join(BASE, "private.pem")
PUBLIC_KEY = os.path.join(BASE, "public.pem")


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
    print(f"OK - Par de llaves generado:")
    print(f"  {PRIVATE_KEY}")
    print(f"  {PUBLIC_KEY}")
    print("! NUNCA distribuyas private.pem con la aplicacion.")


def mostrar_machine():
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
    code = "-".join(parts[:2])
    print(f"Codigo de este equipo: {code}")


def crear_licencia(machine: str, dias: int = 0, issued_str: str = "", expiry_str: str = ""):
    if not os.path.exists(PRIVATE_KEY):
        print("ERROR: No existe private.pem. Ejecuta primero --generate-key")
        return
    with open(PRIVATE_KEY, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)

    if issued_str and expiry_str:
        data = {"machine": machine, "issued": issued_str, "expiry": expiry_str}
    else:
        data = {
            "machine": machine,
            "issued": date.today().isoformat(),
            "expiry": (date.today() + timedelta(days=dias)).isoformat(),
        }

    msg = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    sig = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    data["sig"] = sig.hex()

    lic_path = os.path.join(BASE, "license.lic")
    with open(lic_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"OK - Licencia creada: {lic_path}")
    print(f"  Machine: {machine}")
    print(f"  Emitida: {data['issued']}")
    print(f"  Vence:   {data['expiry']}")
    print("")
    print("! Verifica que el CODIGO del equipo destino sea el correcto.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de licencias SmartEnvio")
    parser.add_argument("--generate-key", action="store_true", help="Generar par RSA")
    parser.add_argument("--create", action="store_true", help="Crear archivo de licencia")
    parser.add_argument("--machine", type=str, default="", help="Codigo del equipo destino")
    parser.add_argument("--dias", type=int, default=0, help="Duracion en dias (requerido si no usas --issued/--expiry)")
    parser.add_argument("--issued", type=str, default="", help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--expiry", type=str, default="", help="Fecha fin YYYY-MM-DD")
    parser.add_argument("--show-machine", action="store_true", help="Mostrar codigo del equipo actual")
    args = parser.parse_args()

    if args.generate_key:
        generar_keypair()
    elif args.create:
        if not args.machine:
            print("ERROR: Usa --machine CODIGO para especificar el equipo destino.")
            print("  Puedes obtener el codigo con: python generar_licencia.py --show-machine")
        elif not args.dias and not (args.issued and args.expiry):
            print("ERROR: Especifica --dias DIAS o --issued FECHA --expiry FECHA.")
        else:
            crear_licencia(args.machine, args.dias, args.issued, args.expiry)
    elif args.show_machine:
        mostrar_machine()
    else:
        parser.print_help()
