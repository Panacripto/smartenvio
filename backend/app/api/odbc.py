from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pyodbc

from app.database.odbc_connector import odbc_connector
from app.database.sqlite_connector import query_one, execute as sqlite_execute

router = APIRouter()


def _load_saved_connstr() -> str:
    row = query_one("SELECT connection_string FROM config_odbc WHERE id=1")
    return row["connection_string"] if row else ""


def _save_connstr(cs: str):
    sqlite_execute("UPDATE config_odbc SET connection_string=?", (cs,))


class PreviewRequest(BaseModel):
    table: str


class TestRequest(BaseModel):
    connection_string: str = ""


@router.get("")
def get_config():
    saved = _load_saved_connstr()
    current = odbc_connector.connection_string or ""
    return {
        "current": current,
        "saved": saved or current,
    }


@router.post("/test")
def test_odbc(body: TestRequest):
    from app.database.odbc_connector import ODBCConnector
    if body.connection_string:
        c = ODBCConnector(body.connection_string)
        success, msg = c.test_connection()
    else:
        success, msg = odbc_connector.test_connection()
    return {"connected": success, "message": msg}


@router.post("/save-config")
def save_config(body: TestRequest):
    if body.connection_string:
        odbc_connector.connection_string = body.connection_string
        _save_connstr(body.connection_string)
    success, msg = odbc_connector.test_connection()
    return {"connected": success, "message": msg}


@router.get("/drivers")
def list_drivers():
    return {"drivers": pyodbc.drivers()}


@router.get("/status")
def connection_status():
    success, msg = odbc_connector.test_connection()
    saved = _load_saved_connstr()
    return {"connected": success, "message": msg, "connection_string": odbc_connector.connection_string, "saved": saved}


@router.get("/tables")
def list_tables():
    try:
        tables = odbc_connector.list_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(400, f"Error: {str(e)}")


@router.post("/preview")
def preview_table(body: PreviewRequest):
    table = body.table
    try:
        sql = f"SELECT * FROM \"{table}\""
        data = odbc_connector.query(sql)
        return {"data": data, "total": len(data)}
    except Exception as e:
        raise HTTPException(400, f"Error consultando tabla: {str(e)}")
