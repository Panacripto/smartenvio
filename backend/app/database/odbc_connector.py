import json, os, pyodbc
from typing import Optional, Any
from app.config import settings


def _load_saved_connstr() -> str:
    try:
        cf = os.path.join(os.path.dirname(os.path.dirname(__file__)), "odbc_config.json")
        with open(cf) as f:
            return json.load(f).get("connection_string", "") or ""
    except:
        return ""


class ODBCConnector:
    def __init__(self, connection_string: Optional[str] = None):
        saved = _load_saved_connstr()
        self.connection_string = self._sanitize(connection_string or saved or settings.odbc_connection_string)
        self._connection: Optional[pyodbc.Connection] = None

    def _sanitize(self, cs: Optional[str]) -> Optional[str]:
        if not cs:
            return None
        cs = cs.strip()
        if cs.upper().startswith("ODBC;"):
            cs = cs[5:]
        return cs

    def connect(self):
        if not self.connection_string:
            raise ValueError("ODBC connection string not configured")
        self._connection = pyodbc.connect(self.connection_string)
        return self._connection

    @property
    def connection(self):
        if self._connection is None:
            self.connect()
        return self._connection

    def query(self, sql: str, params: Optional[list] = None) -> list[dict]:
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=10)
            conn.timeout = 30
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            columns = [col[0] for col in cursor.description]
            rows = []
            for row in cursor.fetchall():
                rows.append(dict(zip(columns, row)))
            cursor.close()
            conn.close()
            return rows
        except pyodbc.Error as e:
            if conn:
                try: conn.close()
                except: pass
            raise
        except Exception as e:
            if conn:
                try: conn.close()
                except: pass
            raise

    def query_to_df_like(self, sql: str, params: Optional[list] = None) -> dict:
        data = self.query(sql, params)
        if not data:
            return {"columns": [], "rows": []}
        return {
            "columns": list(data[0].keys()),
            "rows": [list(row.values()) for row in data],
        }

    def list_tables(self) -> list[str]:
        conn = self.connect()
        cursor = conn.cursor()
        tables = []
        try:
            for row in cursor.tables():
                ttype = str(row.table_type) if row.table_type else ""
                tname = str(row.table_name) if row.table_name else ""
                if ttype == "TABLE" and tname and not tname.startswith("System.") and not tname.startswith("#"):
                    tables.append(tname)
        except:
            pass
        cursor.close()
        if not tables:
            cursor2 = conn.cursor()
            try:
                for row in cursor2.tables():
                    tname = str(row.table_name) if row.table_name else ""
                    if tname and not tname.startswith("System.") and not tname.startswith("#"):
                        tables.append(tname)
            except:
                pass
            cursor2.close()
        return sorted(set(tables))

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self.connect()
            conn.close()
            self._connection = None
            return True, "Conexión exitosa"
        except Exception as e:
            return False, str(e)

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None


odbc_connector = ODBCConnector()
