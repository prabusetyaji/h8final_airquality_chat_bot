# sleepdb_tools.py
import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import csv

# Database file path (di folderkan biar rapih)
DB_PATH = os.getenv("DB_PATH", os.path.join("database", "sleep_data.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

#buat koneksi dulu
def get_connection():
    return sqlite3.connect(DB_PATH,  check_same_thread=False  )

def init_database():
    """
    Initialize the database with sample tables if they don't exist
    """
    # Create the database file if it doesn't exist
   
    with get_connection() as conn:
        cursor = conn.cursor()
        # Stabilitas tulis-baca ringan
        cursor.execute("PRAGMA journal_mode=WAL;")
        # Tabel utama untuk logging tidur & PM2.5
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sleep_logs (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             ts TEXT NOT NULL,          -- ISO timestamp
             pm25 REAL NOT NULL,        -- µg/m³
             sleep_dur_h REAL NOT NULL, -- jumlah jam tidur
             kualitas TEXT,             -- bebas: 'baik/buruk/sedang' dll.
             catatan TEXT               -- catatan opsional
            );
        """)
        conn.commit()
        return f"SQLite initialized at {DB_PATH}"

def add_log(pm25: float, durasi_h: float, kualitas: str = "", catatan: str = "") -> str:
    """
    Simpan satu baris log tidur & PM2.5.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sleep_logs (ts, pm25, durasi_h, kualitas, catatan) VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), float(pm25), float(durasi_h), kualitas, catatan)
        )
        conn.commit()
    return "OK"

def recent_logs(n: int = 10) -> List[Tuple]:
    """
    Ambil N entry terakhir untuk ditampilkan di UI.
    Return list of tuples: (ts, pm25, durasi_h, kualitas, catatan)
    """
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT ts, pm25, durasi_h, kualitas, catatan FROM sleep_logs ORDER BY id DESC LIMIT ?",
            (int(n),)
        )
        return cur.fetchall()

def stats_last(days: int = 7) -> Dict[str, Any]:
    """
    Ringkas rata-rata PM2.5 & durasi dalam X hari terakhir.
    """
    cutoff = (datetime.utcnow() - timedelta(days=int(days))).isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT AVG(pm25), AVG(durasi_h), COUNT(*) FROM sleep_logs WHERE ts >= ?",
            (cutoff,)
        )
        avg_pm, avg_h, cnt = cur.fetchone()
    return {
        "avg_pm": round(avg_pm or 0.0, 1),
        "avg_durasi_h": round(avg_h or 0.0, 1),
        "cnt": cnt or 0
    }





#---- dibawah ini semuanya dari coding tutorial fungsi generik dan tidka termasuk ke fitur utama
def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """
    Execute an SQL query and return the results as a list of dictionaries
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Set row_factory to sqlite3.Row to access columns by name
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        
        # Check if this is a SELECT query
        if query.strip().upper().startswith("SELECT"):
            # Fetch all rows and convert to list of dictionaries
            rows = cursor.fetchall()
            result = [{k: row[k] for k in row.keys()} for row in rows]
        else:
            # For non-SELECT queries, return affected row count
            result = [{"affected_rows": cursor.rowcount}]
            conn.commit()
            
        conn.close()
        return result
    
    except sqlite3.Error as e:
        return [{"error": str(e)}]

def get_table_schema() -> Dict[str, List[Dict[str, str]]]:
    """
    Get the schema of all tables in the database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        schema = {}
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema[table_name] = [
                {
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "pk": bool(col[5])
                }
                for col in columns
            ]
        
        conn.close()
        return schema
    
    except sqlite3.Error as e:
        return {"error": str(e)}

# Function to be used as a tool in the LangGraph agent
def text_to_sql(sql_query: str) -> Dict[str, Any]:
    """
    Execute a SQL query against the database
    
    Args:
        sql_query: The SQL query to execute
        
    Returns:
        Dictionary with SQL query and results
    """
    # Make sure the database exists
    if not os.path.exists(DB_PATH):
        init_database()
    
    # Execute the SQL query
    try:
        results = execute_sql_query(sql_query)
        return {
            "query": sql_query,
            "results": results
        }
    except Exception as e:
        return {
            "query": sql_query,
            "results": [{"error": str(e)}]
        }

def get_database_info() -> Dict[str, Any]:
    """
    Get information about the database schema to help with query construction
    
    Returns:
        Dictionary with database schema and sample data
    """
    # Make sure the database exists
    if not os.path.exists(DB_PATH):
        init_database()
    
    # Get the database schema
    schema = get_table_schema()
    
    # Get sample data for each table (first 3 rows)
    sample_data = {}
    for table_name in schema.keys():
        if isinstance(table_name, str):  # Skip any error entries
            try:
                sample_data[table_name] = execute_sql_query(f"SELECT * FROM {table_name} LIMIT 3")
            except:
                pass
    
    return {
        "schema": schema,
        "sample_data": sample_data
    }

# ---- CLI sederhana ----
if __name__ == "__main__":
    print(init_database())
    print(f"DB path: {DB_PATH}")
    print("Schema:", get_table_schema())
    print("Sample:", get_database_info())