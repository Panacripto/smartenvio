# -*- coding: utf-8 -*-
import subprocess, sys

def probar(cmd, desc):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        out = r.stdout.strip()[:200]
        err = r.stderr.strip()[:200]
        print(f"[{desc}]")
        print(f"  Codigo: {r.returncode}")
        print(f"  Stdout: {out}")
        print(f"  Stderr: {err}")
        if out:
            for ln in r.stdout.splitlines():
                ln = ln.strip().strip('\ufeff').strip('\uFEFF')
                if ln and ln != "UUID" and ln != "SerialNumber" and not ln.startswith("wmic"):
                    print(f"  >>> VALOR UTIL: {ln}")
                    return ln
        print(f"  >>> SIN VALOR UTIL")
        return None
    except Exception as e:
        print(f"[{desc}] ERROR: {e}")
        return None

print("=" * 60)
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print("=" * 60)

print("\n--- PRUEBAS UUID ---")
uuid_val = probar(
    'powershell -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"',
    "PowerShell Get-CimInstance UUID"
)
if not uuid_val:
    probar(
        'powershell -Command "(Get-WmiObject Win32_ComputerSystemProduct).UUID"',
        "PowerShell Get-WmiObject UUID"
    )
if not uuid_val:
    probar("wmic csproduct get uuid", "wmic UUID")

print("\n--- PRUEBAS SERIAL DISCO ---")
probar(
    'powershell -Command "(Get-CimInstance Win32_DiskDrive)[0].SerialNumber"',
    "PowerShell Get-CimInstance Serial"
)
probar(
    'powershell -Command "(Get-WmiObject Win32_DiskDrive)[0].SerialNumber"',
    "PowerShell Get-WmiObject Serial"
)
probar("wmic diskdrive get serialnumber", "wmic Serial")

print("\n" + "=" * 60)
print("COPIEME ESTO COMPLETO Y PEGUELO AQUI")
print("=" * 60)
