from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime

from app.database.sqlite_connector import query, query_one, execute
from app.services.whatsapp_service import enviar_mensaje_whatsapp
from app.schemas.schemas import MensajeCreate, MensajeOut, EnvioMasivoRequest, MensajePersonalizadoRequest

router = APIRouter()


@router.get("")
def listar_mensajes(estado: Optional[str] = None, tipo: Optional[str] = None, skip: int = 0, limit: int = 100):
    sql = "SELECT * FROM mensajes WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    return query(sql, tuple(params))


@router.post("")
def crear_mensaje(msg: MensajeCreate):
    estado = "PROGRAMADO" if msg.programado_para else "PENDIENTE"
    id = execute(
        "INSERT INTO mensajes (cliente_id, cliente_telefono, cliente_nombre, tipo, contenido, estado, programado_para) VALUES (?,?,?,?,?,?,?)",
        (
            msg.cliente_id,
            msg.cliente_telefono,
            msg.cliente_nombre,
            msg.tipo.value if hasattr(msg.tipo, "value") else msg.tipo,
            msg.contenido,
            estado,
            msg.programado_para.isoformat() if msg.programado_para else None,
        ),
    )
    return query_one("SELECT * FROM mensajes WHERE id = ?", (id,))


@router.post("/{mensaje_id}/enviar")
def enviar_mensaje(mensaje_id: int):
    mensaje = query_one("SELECT * FROM mensajes WHERE id = ?", (mensaje_id,))
    if not mensaje:
        raise HTTPException(404, "Mensaje no encontrado")

    resultado = enviar_mensaje_whatsapp(mensaje["cliente_telefono"], mensaje["contenido"])

    if resultado.get("success"):
        execute("UPDATE mensajes SET estado='ENVIADO', enviado_en=datetime('now') WHERE id=?", (mensaje_id,))
    else:
        execute("UPDATE mensajes SET estado='ERROR', error=? WHERE id=?", (resultado.get("error"), mensaje_id))

    return query_one("SELECT * FROM mensajes WHERE id = ?", (mensaje_id,))


@router.post("/enviar-masivo")
def enviar_masivo(request: EnvioMasivoRequest, background_tasks: BackgroundTasks):
    sql = "SELECT * FROM clientes WHERE 1=1"
    params = []

    if request.filtros.get("cliente_ids"):
        ids = request.filtros["cliente_ids"]
        placeholders = ",".join("?" * len(ids))
        sql += f" AND id IN ({placeholders})"
        params.extend(ids)
    if request.filtros.get("solo_con_telefono"):
        sql += " AND telefono IS NOT NULL AND telefono != ''"

    clientes = query(sql, tuple(params))

    if not clientes:
        raise HTTPException(400, "No se encontraron clientes con los filtros especificados")

    plantilla = None
    if request.plantilla_id:
        plantilla = query_one("SELECT * FROM plantillas WHERE id = ?", (request.plantilla_id,))

    for cliente in clientes:
        contenido = plantilla["contenido"] if plantilla else f"Mensaje de tipo: {request.tipo}"
        contenido = contenido.replace("{nombre}", cliente["nombre"] or "")
        contenido = contenido.replace("{codigo}", cliente["codigo"] or "")

        execute(
            "INSERT INTO mensajes (cliente_id, cliente_telefono, cliente_nombre, tipo, contenido, estado, programado_para) VALUES (?,?,?,?,?,?,?)",
            (
                cliente["id"],
                cliente["telefono"],
                cliente["nombre"],
                request.tipo.value if hasattr(request.tipo, "value") else str(request.tipo),
                contenido,
                "PROGRAMADO" if request.programar_para else "PENDIENTE",
                request.programar_para.isoformat() if request.programar_para else None,
            ),
        )

    if not request.programar_para:
        pendientes = query("SELECT id FROM mensajes WHERE estado='PENDIENTE' AND programado_para IS NULL LIMIT 50")
        for msg in pendientes:
            background_tasks.add_task(procesar_envio, msg["id"])

    return {"mensaje": f"{len(clientes)} mensajes creados"}


def procesar_envio(mensaje_id: int):
    from app.database.sqlite_connector import query_one, execute
    mensaje = query_one("SELECT * FROM mensajes WHERE id = ?", (mensaje_id,))
    if mensaje and mensaje["estado"] == "PENDIENTE":
        resultado = enviar_mensaje_whatsapp(mensaje["cliente_telefono"], mensaje["contenido"])
        if resultado.get("success"):
            execute("UPDATE mensajes SET estado='ENVIADO', enviado_en=datetime('now') WHERE id=?", (mensaje_id,))
        else:
            execute("UPDATE mensajes SET estado='ERROR', error=? WHERE id=?", (resultado.get("error"), mensaje_id))


@router.post("/personalizados")
def enviar_personalizados(request: MensajePersonalizadoRequest, background_tasks: BackgroundTasks):
    plantilla = query_one("SELECT * FROM plantillas WHERE id = ?", (request.plantilla_id,))
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")

    placeholders = ",".join("?" * len(request.cliente_ids))
    clientes = query(f"SELECT * FROM clientes WHERE id IN ({placeholders})", tuple(request.cliente_ids))

    if not clientes:
        raise HTTPException(400, "No se encontraron clientes")

    creados = []
    for cliente in clientes:
        contenido = plantilla["contenido"]
        contenido = contenido.replace("{nombre}", cliente["nombre"] or "")
        contenido = contenido.replace("{codigo}", cliente["codigo"] or "")
        contenido = contenido.replace("{telefono}", cliente["telefono"] or "")
        for k, v in request.variables_adicionales.items():
            contenido = contenido.replace(f"{{{k}}}", str(v))

        execute(
            "INSERT INTO mensajes (cliente_id, cliente_telefono, cliente_nombre, tipo, contenido, estado) VALUES (?,?,?,?,?,'PENDIENTE')",
            (cliente["id"], cliente["telefono"], cliente["nombre"], plantilla["tipo"], contenido),
        )
        creados.append(cliente["nombre"])

    pendientes = query("SELECT id FROM mensajes WHERE estado='PENDIENTE' LIMIT 50")
    for msg in pendientes:
        background_tasks.add_task(procesar_envio, msg["id"])

    return {"mensaje": f"Mensajes creados para {len(creados)} clientes", "clientes": creados}
