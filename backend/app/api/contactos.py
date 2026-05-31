from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.sqlite_connector import query, query_one, execute

router = APIRouter()


class ContactoCreate(BaseModel):
    nombre: str
    telefono: str
    email: str = ""
    notas: str = ""


class ContactoUpdate(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    notas: str | None = None


@router.get("")
def listar_contactos(search: str = ""):
    if search:
        s = search.replace("'", "''")
        return query("SELECT * FROM contactos WHERE UPPER(nombre) LIKE ? OR telefono LIKE ? ORDER BY nombre",
                     (f"%{s}%", f"%{s}%"))
    return query("SELECT * FROM contactos ORDER BY nombre")


@router.get("/{contacto_id}")
def obtener_contacto(contacto_id: int):
    c = query_one("SELECT * FROM contactos WHERE id=?", (contacto_id,))
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    return c


@router.post("")
def crear_contacto(body: ContactoCreate):
    cid = execute("INSERT INTO contactos (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)",
                  (body.nombre, body.telefono, body.email, body.notas))
    return {"ok": True, "id": cid}


@router.put("/{contacto_id}")
def actualizar_contacto(contacto_id: int, body: ContactoUpdate):
    c = query_one("SELECT * FROM contactos WHERE id=?", (contacto_id,))
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    campos = {}
    for k in ("nombre", "telefono", "email", "notas"):
        v = getattr(body, k, None)
        if v is not None:
            campos[k] = v
    if campos:
        set_parts = ", ".join(f"{k}=?" for k in campos)
        vals = list(campos.values()) + [contacto_id]
        execute(f"UPDATE contactos SET {set_parts}, updated_at=datetime('now') WHERE id=?", vals)
    return {"ok": True}


@router.delete("/{contacto_id}")
def eliminar_contacto(contacto_id: int):
    execute("DELETE FROM contactos WHERE id=?", (contacto_id,))
    return {"ok": True}
