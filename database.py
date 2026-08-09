import os
import sqlite3
from datetime import datetime


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "curhat.db"
)


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()

    return conn


# ============================================================
# SAVE
# ============================================================

def save_message(
    user_id,
    role,
    content
):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO messages
        (
            user_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            role,
            content,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# HISTORY
# ============================================================

def get_history(
    user_id,
    limit=20
):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    ).fetchall()

    conn.close()

    rows.reverse()

    return rows


# ============================================================
# RESET
# ============================================================

def clear_history(user_id):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM messages
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()