import pyodbc
from .config import SQL_CONN_STR

def get_conn():
    if not SQL_CONN_STR:
        raise RuntimeError("SQL_CONN_STR орнатылмаған (Azure App Settings)")
    return pyodbc.connect(SQL_CONN_STR)

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        # 1️⃣ salons таблица
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='salons' AND xtype='U')
        CREATE TABLE salons (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            start_code NVARCHAR(100) UNIQUE NOT NULL,
            is_active BIT DEFAULT 1
        )
        """)

        conn.commit()
def get_salon_by_start_code(start_code: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name FROM salons WHERE start_code = ? AND is_active = 1",
            (start_code,)
        )
        row = cur.fetchone()
        return row  # (id, name) немесе None
def insert_booking(user_chat_id: int, master_id: str, service_id: str, day: str, time: str, price: int) -> int:
    """
    Жаңа запись қосады, booking_id қайтарады.
    """
    sql = """
    INSERT INTO dbo.bookings (user_chat_id, master_id, service_id, day, time, price, status)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?, ?, 'pending');
    """
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, user_chat_id, master_id, service_id, day, time, price).fetchone()
        conn.commit()
        return int(row[0])

def is_slot_taken(master_id: str, day: str, time: str) -> bool:
    """
    Бір мастерге бір күн/уақыт бронь бар ма?
    (pending/approved болса бос емес деп есептейміз)
    """
    sql = """
    SELECT TOP 1 id
    FROM dbo.bookings
    WHERE master_id = ? AND day = ? AND time = ?
      AND status IN ('pending', 'approved')
    """
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, master_id, day, time).fetchone()
        return row is not None
