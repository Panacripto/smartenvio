from fastapi import APIRouter, HTTPException
import json

from app.database.sqlite_connector import query, query_one, execute
from app.schemas.schemas import ProgramacionCreate

router = APIRouter()


@router.get("/")
def listar_programaciones():
    return query("SELECT * FROM programaciones")


@router.post("/")
def crear_programacion(data: ProgramacionCreate):
    id = execute(
        "INSERT INTO programaciones (nombre, tipo_mensaje, plantilla_id, frecuencia, parametros) VALUES (?,?,?,?,?)",
        (
            data.nombre,
            data.tipo_mensaje.value if hasattr(data.tipo_mensaje, "value") else data.tipo_mensaje,
            data.plantilla_id,
            data.frecuencia.value if hasattr(data.frecuencia, "value") else data.frecuencia,
            json.dumps(data.parametros),
        ),
    )
    return query_one("SELECT * FROM programaciones WHERE id = ?", (id,))


@router.patch("/{programacion_id}/toggle")
def toggle_programacion(programacion_id: int):
    prog = query_one("SELECT * FROM programaciones WHERE id = ?", (programacion_id,))
    if not prog:
        raise HTTPException(404, "Programación no encontrada")
    nuevo = 0 if prog["activo"] else 1
    execute("UPDATE programaciones SET activo=? WHERE id=?", (nuevo, programacion_id))
    return {"activo": bool(nuevo)}


@router.delete("/{programacion_id}")
def delete_programacion(programacion_id: int):
    prog = query_one("SELECT * FROM programaciones WHERE id = ?", (programacion_id,))
    if not prog:
        raise HTTPException(404, "Programación no encontrada")
    execute("DELETE FROM programaciones WHERE id = ?", (programacion_id,))
    return {"ok": True}
