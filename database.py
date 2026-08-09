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
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()

    return conn


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(
    user_id,
    chat_id,
    role,
    content
):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO messages (
            user_id,
            chat_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            chat_id,
            role,
            content,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# GET HISTORY
# ============================================================

def get_history(
    user_id,
    chat_id,
    limit=12
):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE user_id = ?
        AND chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            user_id,
            chat_id,
            limit
        )
    ).fetchall()

    conn.close()


    # Dari lama -> baru
    rows.reverse()

    return rows


# ============================================================
# CLEAR HISTORY
# ============================================================

def clear_history(
    user_id,
    chat_id
):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM messages
        WHERE user_id = ?
        AND chat_id = ?
        """,
        (
            user_id,
            chat_id
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# COUNT
# ============================================================

def get_message_count(
    user_id,
    chat_id
):

    conn = get_connection()

    result = conn.execute(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE user_id = ?
        AND chat_id = ?
        """,
        (
            user_id,
            chat_id
        )
    ).fetchone()

    conn.close()

    return result[0]
