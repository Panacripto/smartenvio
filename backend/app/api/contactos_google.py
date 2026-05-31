import json, os, secrets
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.database.sqlite_connector import execute, query, query_one
from dotenv import load_dotenv

router = APIRouter()

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE, ".env"))

CREDENTIALS_FILE = os.path.join(BASE, "google_credentials.json")
TOKEN_FILE = os.path.join(BASE, "google_token.json")
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]

_state_store: dict = {}


def _get_flow(redirect_uri: str):
    from google_auth_oauthlib.flow import Flow
    import json
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
        client_type = "web" if "web" in creds else "installed"
        config = {client_type: creds[client_type]}
        flow = Flow.from_client_config(config, scopes=SCOPES)
    else:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(400, "No se encontraron credenciales de Google. Verifica google_credentials.json o GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET en .env")
        flow = Flow.from_client_config({
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    return flow


@router.get("/google/auth-url")
def get_auth_url():
    flow = _get_flow("http://localhost:8000/api/contactos/google/callback")
    state = secrets.token_urlsafe(32)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
    )
    _state_store[state] = {
        "session": flow.oauth2session,
        "code_verifier": flow.code_verifier,
    }
    return {"auth_url": auth_url}


@router.get("/google/callback")
def callback(code: str = "", state: str = "", error: str = ""):
    try:
        if error:
            return HTMLResponse(f"<script>window.close()</script><h2>Error de Google: {error}</h2><p>Puede cerrar esta ventana.</p>")
        if state not in _state_store:
            return HTMLResponse("<script>window.close()</script><h2>Estado inválido</h2><p>Puede cerrar esta ventana.</p>")
        saved = _state_store.pop(state)

        flow = _get_flow("http://localhost:8000/api/contactos/google/callback")
        flow.oauth2session = saved["session"]
        flow.code_verifier = saved["code_verifier"]
        flow.fetch_token(code=code)

        with open(TOKEN_FILE, "w") as f:
            f.write(flow.credentials.to_json())

        from googleapiclient.discovery import build
        service = build("people", "v1", credentials=flow.credentials)
        results = service.people().connections().list(
            resourceName="people/me",
            pageSize=1000,
            personFields="names,phoneNumbers,emailAddresses",
        ).execute()

        connections = results.get("connections", [])
        imported = 0
        for person in connections:
            names = person.get("names", [])
            phones = person.get("phoneNumbers", [])
            emails = person.get("emailAddresses", [])
            if not names or not phones:
                continue
            nombre = names[0].get("displayName", "")
            telefono = phones[0].get("value", "").replace(" ", "").replace("-", "").lstrip("+")
            email = emails[0].get("value", "") if emails else ""
            if nombre and telefono:
                existente = query_one("SELECT id FROM contactos WHERE telefono=?", (telefono,))
                if existente:
                    continue
                execute("INSERT INTO contactos (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)",
                        (nombre, telefono, email, "Importado de Google"))
                imported += 1

        return HTMLResponse(
            f"<script>window.close()</script>"
            f"<h2>Importación completada</h2>"
            f"<p>{imported} contactos importados (se omitieron {len(connections)-imported} duplicados).</p>"
            f"<p>Esta ventana se cerrará automáticamente.</p>"
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        msg = f"<script>console.log({repr(tb)})</script><h2>Error interno</h2><pre>{e}</pre><p>Puede cerrar esta ventana.</p>"
        return HTMLResponse(msg)


@router.post("/google/importar")
def importar_google():
    if not os.path.exists(TOKEN_FILE):
        raise HTTPException(400, "No hay sesión de Google. Use el botón 'Conectar con Google' primero.")

    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        raise HTTPException(400, "Sesión expirada. Conéctese de nuevo con Google.")

    from googleapiclient.discovery import build
    service = build("people", "v1", credentials=creds)
    results = service.people().connections().list(
        resourceName="people/me",
        pageSize=1000,
        personFields="names,phoneNumbers,emailAddresses",
    ).execute()

    connections = results.get("connections", [])
    imported = 0
    for person in connections:
        names = person.get("names", [])
        phones = person.get("phoneNumbers", [])
        emails = person.get("emailAddresses", [])
        if not names or not phones:
            continue
        nombre = names[0].get("displayName", "")
        telefono = phones[0].get("value", "").replace(" ", "").replace("-", "").lstrip("+")
        email = emails[0].get("value", "") if emails else ""
        if nombre and telefono:
            existente = query_one("SELECT id FROM contactos WHERE telefono=?", (telefono,))
            if existente:
                continue
            execute("INSERT INTO contactos (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)",
                    (nombre, telefono, email, "Importado de Google"))
            imported += 1

    total = query("SELECT COUNT(*) as c FROM contactos WHERE notas='Importado de Google'")
    return {"importados": imported, "omitidos_duplicados": len(connections) - imported, "total_contactos": total[0]["c"] if total else imported}


@router.get("/google/status")
def google_status():
    if not os.path.exists(TOKEN_FILE):
        return {"conectado": False}
    from google.oauth2.credentials import Credentials
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return {"conectado": creds.valid}
    except:
        return {"conectado": False}
