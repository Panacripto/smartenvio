import json, os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pyodbc

from app.database.odbc_connector import odbc_connector

router = APIRouter()

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "odbc_config.json")


def _load_saved_connstr() -> str:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f).get("connection_string", "") or ""
    except:
        return ""


def _save_connstr(cs: str):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"connection_string": cs}, f)


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
