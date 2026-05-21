import sqlite3
import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from app.config import settings


def _get_db_path():
    url = settings.database_url
    if url.startswith("sqlite:///"):
        path = url[10:]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        return path
    return "data/app.db"


DB_PATH = _get_db_path()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    with get_db() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nombre TEXT,
                telefono TEXT,
                email TEXT,
                limite_credito REAL DEFAULT 0,
                saldo_pendiente REAL DEFAULT 0,
                direccion TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento TEXT UNIQUE,
                cliente_codigo TEXT,
                cliente_nombre TEXT,
                fecha TEXT,
                total REAL DEFAULT 0,
                estado TEXT DEFAULT 'PENDIENTE',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento TEXT UNIQUE,
                proveedor TEXT,
                fecha TEXT,
                total REAL DEFAULT 0,
                estado TEXT DEFAULT 'PENDIENTE',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                descripcion TEXT,
                cantidad REAL DEFAULT 0,
                precio_costo REAL DEFAULT 0,
                precio_venta REAL DEFAULT 0,
                stock_minimo REAL DEFAULT 0,
                ubicacion TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cuentas_cobrar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento TEXT,
                cliente_codigo TEXT,
                cliente_nombre TEXT,
                fecha_emision TEXT,
                fecha_vencimiento TEXT,
                monto_original REAL DEFAULT 0,
                saldo_pendiente REAL DEFAULT 0,
                dias_vencido INTEGER DEFAULT 0,
                estado TEXT DEFAULT 'PENDIENTE',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cuentas_pagar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento TEXT,
                proveedor TEXT,
                fecha_emision TEXT,
                fecha_vencimiento TEXT,
                monto_original REAL DEFAULT 0,
                saldo_pendiente REAL DEFAULT 0,
                dias_vencido INTEGER DEFAULT 0,
                estado TEXT DEFAULT 'PENDIENTE',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                cliente_telefono TEXT,
                cliente_nombre TEXT,
                tipo TEXT,
                contenido TEXT,
                estado TEXT DEFAULT 'PENDIENTE',
                programado_para TEXT,
                enviado_en TEXT,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );

            CREATE TABLE IF NOT EXISTS plantillas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                tipo TEXT,
                contenido TEXT,
                variables TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS programaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                tipo_mensaje TEXT,
                plantilla_id INTEGER,
                frecuencia TEXT,
                parametros TEXT DEFAULT '{}',
                activo INTEGER DEFAULT 1,
                ultima_ejecucion TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (plantilla_id) REFERENCES plantillas(id)
            );

            CREATE TABLE IF NOT EXISTS query_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla TEXT UNIQUE,
                sql_query TEXT,
                activo INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS factura_digital_envios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento TEXT NOT NULL,
                cliente_codigo TEXT,
                telefono TEXT,
                filtro TEXT,
                enviado_en TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                mensaje TEXT NOT NULL DEFAULT '',
                intervalo TEXT NOT NULL DEFAULT 'diario',
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT,
                activo INTEGER DEFAULT 1,
                clientes_seleccionados TEXT DEFAULT '[]',
                hora_envio TEXT,
                hora_fin TEXT,
                repetir_cada INTEGER DEFAULT 0,
                enviados_total INTEGER DEFAULT 0,
                fallidos_total INTEGER DEFAULT 0,
                veces_ejecutada INTEGER DEFAULT 0,
                ultima_ejecucion TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS campaign_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                archivo_nombre TEXT NOT NULL,
                archivo_base64 TEXT NOT NULL,
                archivo_mimetype TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS campaign_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                ejecucion_numero INTEGER DEFAULT 1,
                enviados INTEGER DEFAULT 0,
                fallidos INTEGER DEFAULT 0,
                total_destinos INTEGER DEFAULT 0,
                ejecutado_en TEXT DEFAULT (datetime('now')),
                detalles TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );
        """)
        # Migrations for existing DBs
        for col in ("hora_envio TEXT", "hora_fin TEXT", "repetir_cada INTEGER DEFAULT 0"):
            try:
                conn.execute(f"ALTER TABLE campaigns ADD COLUMN {col}")
            except:
                pass
