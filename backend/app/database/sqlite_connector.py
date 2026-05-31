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

            CREATE TABLE IF NOT EXISTS contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL,
                email TEXT DEFAULT '',
                notas TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
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

            CREATE TABLE IF NOT EXISTS config_smartenvio (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                activo INTEGER NOT NULL DEFAULT 1
            );
            INSERT OR IGNORE INTO config_smartenvio (id, activo) VALUES (1, 1);

            CREATE TABLE IF NOT EXISTS config_smartenvio_reglas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dias INTEGER NOT NULL UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1,
                etiqueta TEXT NOT NULL DEFAULT '',
                mensaje TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS config_odbc (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                connection_string TEXT NOT NULL DEFAULT ''
            );
            INSERT OR IGNORE INTO config_odbc (id, connection_string) VALUES (1, '');

            CREATE TABLE IF NOT EXISTS config_facturadigital (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mensaje TEXT NOT NULL DEFAULT '',
                auto_activo INTEGER NOT NULL DEFAULT 0,
                auto_intervalo INTEGER NOT NULL DEFAULT 5,
                enviar_pdf INTEGER NOT NULL DEFAULT 1,
                incluir_sello INTEGER NOT NULL DEFAULT 1,
                empresa_razon_social TEXT NOT NULL DEFAULT '',
                empresa_rif TEXT NOT NULL DEFAULT '',
                empresa_direccion TEXT NOT NULL DEFAULT '',
                empresa_telefono TEXT NOT NULL DEFAULT '',
                empresa_logo TEXT NOT NULL DEFAULT ''
            );
            INSERT OR IGNORE INTO config_facturadigital (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS config_cobranza (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mensaje TEXT NOT NULL DEFAULT ''
            );
            INSERT OR IGNORE INTO config_cobranza (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS config_footer (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                texto TEXT NOT NULL DEFAULT ''
            );
            INSERT OR IGNORE INTO config_footer (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS config_gestionpagos (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mensaje TEXT NOT NULL DEFAULT '',
                telefono1 TEXT NOT NULL DEFAULT '',
                telefono2 TEXT NOT NULL DEFAULT '',
                telefono3 TEXT NOT NULL DEFAULT '',
                activo INTEGER NOT NULL DEFAULT 0
            );
            INSERT OR IGNORE INTO config_gestionpagos (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS pagos_proveedores (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS pagos_documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_codigo TEXT NOT NULL,
                numero TEXT NOT NULL DEFAULT '',
                monto REAL NOT NULL DEFAULT 0,
                fecha_vencimiento TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (proveedor_codigo) REFERENCES pagos_proveedores(codigo)
            );
        """)
        # Migrations for existing DBs
        migraciones = [
            ("campaigns", "hora_envio TEXT"),
            ("campaigns", "hora_fin TEXT"),
            ("campaigns", "repetir_cada INTEGER DEFAULT 0"),
            ("campaigns", "filtro TEXT"),
            ("config_facturadigital", "formato_pdf TEXT DEFAULT 'carta'"),
            ("campaigns", "proximo_reintento TEXT"),
            ("config_facturadigital", "telefono_catchall TEXT DEFAULT ''"),
            ("config_facturadigital", "catchall_activo INTEGER DEFAULT 0"),
        ]
        for tbl, col in migraciones:
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col}")
            except:
                pass
