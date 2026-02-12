import pyodbc
from .config import SQL_CONN_STR

def get_conn():
    if not SQL_CONN_STR:
        raise RuntimeError("SQL_CONN_STR орнатылмаған (Azure App Settings)")
    return pyodbc.connect(SQL_CONN_STR)

def init_db():
    """
    Таблица жоқ болса — өзі жасайды.
    """
    sql = """
    IF OBJECT_ID('dbo.bookings', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.bookings (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_chat_id BIGINT NOT NULL,
            master_id NVARCHAR(50) NOT NULL,
            service_id NVARCHAR(50) NOT NULL,
            day NVARCHAR(50) NOT NULL,
            time NVARCHAR(50) NOT NULL,
            price INT NOT NULL,
            status NVARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
        );
    END
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()

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
