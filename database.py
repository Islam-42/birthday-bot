import aiosqlite
import os


# На FadeHost есть папка /data.
# На Mac её нет, поэтому используется локальный birthdays.db.
if os.path.exists("/data"):
    DB_PATH = "/data/birthdays.db"
else:
    DB_PATH = "birthdays.db"


# =========================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# =========================

async def init_db():
    db = await aiosqlite.connect(DB_PATH)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS sent_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            birthday_id INTEGER NOT NULL,
            reminder_date TEXT NOT NULL,
            UNIQUE(birthday_id, reminder_date)
        )
    """)

    await db.commit()
    await db.close()


# =========================
# ДОБАВЛЕНИЕ
# =========================

async def add_birthday(
    user_id: int,
    name: str,
    day: int,
    month: int
):
    db = await aiosqlite.connect(DB_PATH)

    await db.execute(
        """
        INSERT INTO birthdays (
            user_id,
            name,
            day,
            month
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            name,
            day,
            month
        )
    )

    await db.commit()
    await db.close()


# =========================
# ПОЛУЧЕНИЕ ДНЕЙ РОЖДЕНИЯ
# =========================

async def get_birthdays(user_id: int):
    db = await aiosqlite.connect(DB_PATH)

    cursor = await db.execute(
        """
        SELECT id, name, day, month
        FROM birthdays
        WHERE user_id = ?
        ORDER BY month, day
        """,
        (user_id,)
    )

    birthdays = await cursor.fetchall()

    await cursor.close()
    await db.close()

    return birthdays


# =========================
# ПОЛУЧЕНИЕ ВСЕХ ДНЕЙ РОЖДЕНИЯ
# =========================

async def get_all_birthdays():
    db = await aiosqlite.connect(DB_PATH)

    cursor = await db.execute(
        """
        SELECT id, user_id, name, day, month
        FROM birthdays
        """
    )

    birthdays = await cursor.fetchall()

    await cursor.close()
    await db.close()

    return birthdays


# =========================
# УДАЛЕНИЕ
# =========================

async def delete_birthday(
    user_id: int,
    birthday_id: int
):
    db = await aiosqlite.connect(DB_PATH)

    await db.execute(
        """
        DELETE FROM birthdays
        WHERE id = ?
        AND user_id = ?
        """,
        (
            birthday_id,
            user_id
        )
    )

    await db.execute(
        """
        DELETE FROM sent_reminders
        WHERE birthday_id = ?
        """,
        (birthday_id,)
    )

    await db.commit()
    await db.close()


# =========================
# ИЗМЕНЕНИЕ
# =========================

async def update_birthday(
    user_id: int,
    birthday_id: int,
    name: str,
    day: int,
    month: int
):
    db = await aiosqlite.connect(DB_PATH)

    await db.execute(
        """
        UPDATE birthdays
        SET name = ?,
            day = ?,
            month = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            name,
            day,
            month,
            birthday_id,
            user_id
        )
    )

    await db.commit()
    await db.close()


# =========================
# ПРОВЕРКА ОТПРАВЛЕННОГО
# НАПОМИНАНИЯ
# =========================

async def reminder_was_sent(
    birthday_id: int,
    reminder_date: str
):
    db = await aiosqlite.connect(DB_PATH)

    cursor = await db.execute(
        """
        SELECT 1
        FROM sent_reminders
        WHERE birthday_id = ?
        AND reminder_date = ?
        """,
        (
            birthday_id,
            reminder_date
        )
    )

    result = await cursor.fetchone()

    await cursor.close()
    await db.close()

    return result is not None


# =========================
# СОХРАНЕНИЕ ОТПРАВЛЕННОГО
# НАПОМИНАНИЯ
# =========================

async def save_sent_reminder(
    birthday_id: int,
    reminder_date: str
):
    db = await aiosqlite.connect(DB_PATH)

    await db.execute(
        """
        INSERT OR IGNORE INTO sent_reminders (
            birthday_id,
            reminder_date
        )
        VALUES (?, ?)
        """,
        (
            birthday_id,
            reminder_date
        )
    )

    await db.commit()
    await db.close()
