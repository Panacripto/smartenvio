from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class TipoMensaje(str, Enum):
    RECORDATORIO_PAGO = "recordatorio_pago"
    CONFIRMACION_PEDIDO = "confirmacion_pedido"
    PROMOCION = "promocion"
    FACTURA_DIGITAL = "factura_digital"
    PERSONALIZADO = "personalizado"


class Frecuencia(str, Enum):
    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSUAL = "mensual"
    UNA_VEZ = "una_vez"


class MensajeCreate(BaseModel):
    cliente_id: Optional[int] = None
    cliente_telefono: str
    cliente_nombre: str = ""
    tipo: TipoMensaje = TipoMensaje.PERSONALIZADO
    contenido: str
    programado_para: Optional[datetime] = None


class MensajeOut(BaseModel):
    id: int
    cliente_id: Optional[int] = None
    cliente_telefono: str
    cliente_nombre: str
    tipo: str
    contenido: str
    estado: str
    programado_para: Optional[datetime] = None
    enviado_en: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlantillaCreate(BaseModel):
    nombre: str
    tipo: TipoMensaje
    contenido: str
    variables: list[str] = []


class ODBCQuery(BaseModel):
    sql: str
    params: list[Any] = []


class MensajePersonalizadoRequest(BaseModel):
    cliente_ids: list[int]
    plantilla_id: int
    variables_adicionales: dict = {}


class EnvioMasivoRequest(BaseModel):
    tipo: TipoMensaje
    filtros: dict = {}
    plantilla_id: Optional[int] = None
    programar_para: Optional[datetime] = None


class ProgramacionCreate(BaseModel):
    nombre: str
    tipo_mensaje: TipoMensaje
    plantilla_id: Optional[int] = None
    frecuencia: Frecuencia
    parametros: dict = {}
