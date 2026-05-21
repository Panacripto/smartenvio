import subprocess, hashlib

def get_uuid():
    cmds = [
        'powershell -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"',
        'powershell -Command "(Get-WmiObject Win32_ComputerSystemProduct).UUID"',
        'wmic csproduct get uuid'
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            for ln in r.stdout.splitlines():
                ln = ln.strip().strip("\ufeff").strip("\uFEFF")
                if ln and ln != "UUID" and not ln.startswith("wmic"):
                    return ln
        except:
            pass
    return None

def get_serial():
    cmds = [
        'powershell -Command "(Get-CimInstance Win32_DiskDrive)[0].SerialNumber"',
        'powershell -Command "(Get-WmiObject Win32_DiskDrive)[0].SerialNumber"',
        'wmic diskdrive get serialnumber'
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            for ln in r.stdout.splitlines():
                ln = ln.strip().strip("\ufeff").strip("\uFEFF")
                if ln and ln != "SerialNumber" and not ln.startswith("wmic"):
                    return ln
        except:
            pass
    return None

uuid = get_uuid()
serial = get_serial()
parts = []
if uuid:
    parts.append(hashlib.md5(uuid.encode()).hexdigest()[:8])
if serial:
    parts.append(hashlib.md5(serial.encode()).hexdigest()[:8])
codigo = "-".join(parts[:2]) if parts else "FALLO TOTAL"

print("UUID            :", uuid or "(no detectado)")
print("Serial Disco    :", serial or "(no detectado)")
print("CODIGO MAQUINA  :", codigo)
print()
if codigo == "FALLO TOTAL":
    print("PRUEBE MANUALMENTE EN POWERSHELL:")
    print('  (Get-CimInstance Win32_ComputerSystemProduct).UUID')
    print('  (Get-CimInstance Win32_DiskDrive)[0].SerialNumber')
