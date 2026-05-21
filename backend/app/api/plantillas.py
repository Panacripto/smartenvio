from fastapi import APIRouter, HTTPException
import json

from app.database.sqlite_connector import query, query_one, execute
from app.schemas.schemas import PlantillaCreate

router = APIRouter()


@router.get("/")
def listar_plantillas():
    return query("SELECT * FROM plantillas ORDER BY nombre")


@router.post("/")
def crear_plantilla(data: PlantillaCreate):
    exists = query_one("SELECT id FROM plantillas WHERE nombre = ?", (data.nombre,))
    if exists:
        raise HTTPException(400, "Ya existe una plantilla con ese nombre")

    id = execute(
        "INSERT INTO plantillas (nombre, tipo, contenido, variables) VALUES (?,?,?,?)",
        (
            data.nombre,
            data.tipo.value if hasattr(data.tipo, "value") else data.tipo,
            data.contenido,
            json.dumps(data.variables),
        ),
    )
    return query_one("SELECT * FROM plantillas WHERE id = ?", (id,))


@router.get("/{plantilla_id}")
def get_plantilla(plantilla_id: int):
    p = query_one("SELECT * FROM plantillas WHERE id = ?", (plantilla_id,))
    if not p:
        raise HTTPException(404, "Plantilla no encontrada")
    return p


@router.put("/{plantilla_id}")
def update_plantilla(plantilla_id: int, data: PlantillaCreate):
    p = query_one("SELECT * FROM plantillas WHERE id = ?", (plantilla_id,))
    if not p:
        raise HTTPException(404, "Plantilla no encontrada")

    execute(
        "UPDATE plantillas SET nombre=?, tipo=?, contenido=?, variables=?, updated_at=datetime('now') WHERE id=?",
        (
            data.nombre,
            data.tipo.value if hasattr(data.tipo, "value") else data.tipo,
            data.contenido,
            json.dumps(data.variables),
            plantilla_id,
        ),
    )
    return query_one("SELECT * FROM plantillas WHERE id = ?", (plantilla_id,))


@router.delete("/{plantilla_id}")
def delete_plantilla(plantilla_id: int):
    p = query_one("SELECT * FROM plantillas WHERE id = ?", (plantilla_id,))
    if not p:
        raise HTTPException(404, "Plantilla no encontrada")
    execute("DELETE FROM plantillas WHERE id = ?", (plantilla_id,))
    return {"ok": True}
