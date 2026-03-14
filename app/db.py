import pyodbc
from typing import Optional
from .config import SQL_CONN_STR


def get_conn():
    if not SQL_CONN_STR:
        raise RuntimeError("SQL_CONN_STR орнатылмаған (Azure App Settings)")
    return pyodbc.connect(SQL_CONN_STR)

def add_closed_slot(salon_id: int, master_id: str | None, day: str, time: str):
    sql = """
    INSERT INTO dbo.closed_slots (salon_id, master_id, day, time)
    VALUES (?, ?, ?, ?)
    """
    with get_conn() as conn:
        conn.execute(sql, salon_id, master_id, day, time)
        conn.commit()

def remove_closed_slot(salon_id: int, master_id: str | None, day: str, time: str):
    sql = """
    DELETE FROM dbo.closed_slots
    WHERE salon_id = ?
      AND day = ?
      AND time = ?
      AND (master_id = ? OR (? IS NULL AND master_id IS NULL))
    """
    with get_conn() as conn:
        conn.execute(sql, salon_id, day, time, master_id, master_id)
        conn.commit()
        
def get_active_salons():
    sql = """
    SELECT id, name
    FROM dbo.salons
    WHERE is_active = 1
    ORDER BY id
    """
    with get_conn() as conn:
        return conn.execute(sql).fetchall()

def is_slot_closed(salon_id: int, master_id: str, day: str, time: str) -> bool:
    sql = """
    SELECT TOP 1 id
    FROM dbo.closed_slots
    WHERE salon_id = ?
      AND day = ?
      AND time = ?
      AND (master_id = ? OR master_id IS NULL)
    """
    with get_conn() as conn:
        row = conn.execute(sql, salon_id, day, time, master_id).fetchone()
        return bool(row)
    
def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        # -------------------------
        # salons
        # -------------------------
        cur.execute("""
        IF OBJECT_ID('dbo.salons', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.salons (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(255) NOT NULL,
                start_code NVARCHAR(100) NOT NULL,
                is_active BIT NULL DEFAULT 1,
                admin_chat_id BIGINT NULL
            );
        END
        """)

        # Егер бұрыннан бар salons таблицасында admin_chat_id жоқ болса — қосамыз
        cur.execute("""
        IF COL_LENGTH('dbo.salons', 'admin_chat_id') IS NULL
        BEGIN
            ALTER TABLE dbo.salons
            ADD admin_chat_id BIGINT NULL;
        END
        """)

        # Егер UNIQUE constraint жоқ болса, start_code-қа unique қоямыз
        cur.execute("""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'UQ_salons_start_code'
              AND object_id = OBJECT_ID('dbo.salons')
        )
        BEGIN
            ALTER TABLE dbo.salons
            ADD CONSTRAINT UQ_salons_start_code UNIQUE (start_code);
        END
        """)

        # -------------------------
        # masters
        # -------------------------
        cur.execute("""
        IF OBJECT_ID('dbo.masters', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.masters (
                id INT IDENTITY(1,1) PRIMARY KEY,
                salon_id INT NOT NULL,
                name NVARCHAR(255) NOT NULL,
                is_active BIT NULL DEFAULT 1
            );
        END
        """)

        # FK masters -> salons
        cur.execute("""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_masters_salons'
        )
        BEGIN
            ALTER TABLE dbo.masters
            ADD CONSTRAINT FK_masters_salons
            FOREIGN KEY (salon_id) REFERENCES dbo.salons(id);
        END
        """)

        # -------------------------
        # services
        # -------------------------
        cur.execute("""
        IF OBJECT_ID('dbo.services', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.services (
                id NVARCHAR(100) NOT NULL,
                salon_id INT NOT NULL,
                title NVARCHAR(255) NOT NULL,
                price INT NOT NULL,
                is_active BIT NULL DEFAULT 1,
                CONSTRAINT PK_services PRIMARY KEY (id, salon_id)
            );
        END
        """)

        # FK services -> salons
        cur.execute("""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_services_salons'
        )
        BEGIN
            ALTER TABLE dbo.services
            ADD CONSTRAINT FK_services_salons
            FOREIGN KEY (salon_id) REFERENCES dbo.salons(id);
        END
        """)

        # -------------------------
        # bookings
        # -------------------------
        cur.execute("""
        IF OBJECT_ID('dbo.bookings', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.bookings (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_chat_id BIGINT NOT NULL,
                master_id NVARCHAR(100) NOT NULL,
                service_id NVARCHAR(100) NOT NULL,
                day NVARCHAR(50) NOT NULL,
                time NVARCHAR(20) NOT NULL,
                price INT NOT NULL,
                status NVARCHAR(50) NOT NULL,
                created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                salon_id INT NOT NULL
            );
        END
        """)

        # FK bookings -> salons
        cur.execute("""
        IF NOT EXISTS (
            SELECT 1
            FROM sys.foreign_keys
            WHERE name = 'FK_bookings_salons'
        )
        BEGIN
            ALTER TABLE dbo.bookings
            ADD CONSTRAINT FK_bookings_salons
            FOREIGN KEY (salon_id) REFERENCES dbo.salons(id);
        END
        """)

        conn.commit()
def get_closed_days(salon_id: int):
    sql = """
    SELECT day
    FROM dbo.closed_days
    WHERE salon_id = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, salon_id).fetchall()
        return [str(r[0]) for r in rows]


def add_closed_day(salon_id: int, day: str, note: str | None = None):
    sql = """
    IF NOT EXISTS (
        SELECT 1
        FROM dbo.closed_days
        WHERE salon_id = ? AND day = ?
    )
    BEGIN
        INSERT INTO dbo.closed_days (salon_id, day, note)
        VALUES (?, ?, ?)
    END
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, salon_id, day, salon_id, day, note)
        conn.commit()
        
def remove_closed_day(salon_id: int, day: str):
    sql = """
    DELETE FROM dbo.closed_days
    WHERE salon_id = ? AND day = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, salon_id, day)
        conn.commit()
def get_active_bookings_by_salon_and_day(salon_id: int, day: str):
    sql = """
    SELECT
        b.id,
        b.user_chat_id,
        b.client_phone,
        b.client_name,
        b.day,
        b.time,
        m.name AS master_name,
        s.title AS service_title,
        b.price,
        b.calendar_event_id
    FROM dbo.bookings b
    LEFT JOIN dbo.masters m
        ON CAST(m.id AS NVARCHAR(MAX)) = CAST(b.master_id AS NVARCHAR(MAX))
       AND m.salon_id = b.salon_id
    LEFT JOIN dbo.services s
        ON CAST(s.id AS NVARCHAR(MAX)) = CAST(b.service_id AS NVARCHAR(MAX))
       AND s.salon_id = b.salon_id
    WHERE b.salon_id = ?
      AND b.day = ?
      AND b.status IN ('pending', 'approved')
    ORDER BY b.time
    """
    with get_conn() as conn:
        cur = conn.cursor()
        return cur.execute(sql, salon_id, day).fetchall()
    
def get_salon_admin_chat_id(salon_id: int) -> Optional[int]:
    sql = "SELECT admin_chat_id FROM dbo.salons WHERE id = ?"
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, salon_id).fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])


def get_salon_by_start_code(start_code: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name FROM dbo.salons WHERE start_code = ? AND is_active = 1",
            (start_code,)
        )
        return cur.fetchone()


def get_masters_by_salon(salon_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name FROM dbo.masters WHERE salon_id = ? AND is_active = 1 ORDER BY id",
            (salon_id,)
        )
        return cur.fetchall()


def get_services_by_salon(salon_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, price FROM dbo.services WHERE salon_id = ? AND is_active = 1 ORDER BY id",
            (salon_id,)
        )
        return cur.fetchall()


def insert_booking(
    user_chat_id: int,
    salon_id: int,
    master_id: str,
    service_id: str,
    day: str,
    time: str,
    price: int,
    client_phone: str | None = None,
    client_name: str | None = None
) -> int:
    sql = """
    INSERT INTO dbo.bookings
    (user_chat_id, salon_id, master_id, service_id, day, time, price, status, client_phone, client_name)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?);
    """

    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(
            sql,
            user_chat_id,
            salon_id,
            master_id,
            service_id,
            day,
            time,
            price,
            client_phone,
            client_name
        ).fetchone()
        conn.commit()
        return int(row[0])

        

def is_slot_taken(
    salon_id: int,
    master_id: str,
    day: str,
    time: str
) -> bool:
    sql = """
    SELECT TOP 1 id
    FROM dbo.bookings
    WHERE salon_id = ?
      AND master_id = ?
      AND day = ?
      AND time = ?
      AND status IN ('pending', 'approved')
    """

    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, salon_id, master_id, day, time).fetchone()
        return row is not None
def set_booking_calendar_event_id(booking_id: int, calendar_event_id: str):
    sql = """
    UPDATE dbo.bookings
    SET calendar_event_id = ?
    WHERE id = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, calendar_event_id, booking_id)
        conn.commit()


def get_booking_for_cancel(booking_id: int):
    sql = """
    SELECT id, user_chat_id, salon_id, master_id, service_id, day, time, price, status, calendar_event_id
    FROM dbo.bookings
    WHERE id = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, booking_id).fetchone()
        return row

def get_user_active_bookings(user_chat_id: int):
    sql = """
    SELECT
        b.id,
        b.day,
        b.time,
        b.status,
        m.name AS master_name,
        s.title AS service_title,
        b.price
    FROM dbo.bookings b
    LEFT JOIN dbo.masters m
        ON CAST(m.id AS NVARCHAR(MAX)) = CAST(b.master_id AS NVARCHAR(MAX))
       AND m.salon_id = b.salon_id
    LEFT JOIN dbo.services s
        ON CAST(s.id AS NVARCHAR(MAX)) = CAST(b.service_id AS NVARCHAR(MAX))
       AND s.salon_id = b.salon_id
    WHERE b.user_chat_id = ?
      AND b.status IN ('pending', 'approved')
    ORDER BY b.day, b.time
    """

    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, user_chat_id).fetchall()
        return rows
    
def cancel_booking(booking_id: int):
    sql = """
    UPDATE dbo.bookings
    SET status = 'cancelled'
    WHERE id = ?
      AND status <> 'cancelled'
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, booking_id)
        conn.commit()


def get_booking_full_info(booking_id: int):
    sql = """
    SELECT
        b.id,
        b.user_chat_id,
        b.salon_id,
        b.master_id,
        b.service_id,
        b.day,
        b.time,
        b.price,
        b.status,
        b.calendar_event_id,
        m.name AS master_name,
        s.title AS service_title
    FROM dbo.bookings b
    LEFT JOIN dbo.masters m
        ON CAST(m.id AS NVARCHAR(MAX)) = CAST(b.master_id AS NVARCHAR(MAX))
       AND m.salon_id = b.salon_id
    LEFT JOIN dbo.services s
        ON CAST(s.id AS NVARCHAR(MAX)) = CAST(b.service_id AS NVARCHAR(MAX))
       AND s.salon_id = b.salon_id
    WHERE b.id = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, booking_id).fetchone()
        return row

if __name__ == "__main__":
    init_db()
    print("Database structure дайын ✅")