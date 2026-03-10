import pyodbc
from typing import Optional
from .config import SQL_CONN_STR


def get_conn():
    if not SQL_CONN_STR:
        raise RuntimeError("SQL_CONN_STR орнатылмаған (Azure App Settings)")
    return pyodbc.connect(SQL_CONN_STR)


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
    price: int
) -> int:
    sql = """
    INSERT INTO dbo.bookings
    (user_chat_id, salon_id, master_id, service_id, day, time, price, status)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending');
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
            price
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


if __name__ == "__main__":
    init_db()
    print("Database structure дайын ✅")