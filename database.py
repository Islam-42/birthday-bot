import aiosqlite


async def init_db():
    db = await aiosqlite.connect("birthdays.db")

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


async def add_birthday(user_id, name, day, month):
    db = await aiosqlite.connect("birthdays.db")

    await db.execute(
        """
        INSERT INTO birthdays (user_id, name, day, month)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, name, day, month)
    )

    await db.commit()
    await db.close()


async def get_birthdays(user_id):
    db = await aiosqlite.connect("birthdays.db")

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

    await db.close()

    return birthdays


async def get_all_birthdays():
    db = await aiosqlite.connect("birthdays.db")

    cursor = await db.execute(
        """
        SELECT id, user_id, name, day, month
        FROM birthdays
        """
    )

    birthdays = await cursor.fetchall()

    await db.close()

    return birthdays


async def delete_birthday(user_id, birthday_id):
    db = await aiosqlite.connect("birthdays.db")

    await db.execute(
        """
        DELETE FROM birthdays
        WHERE id = ? AND user_id = ?
        """,
        (birthday_id, user_id)
    )

    await db.commit()
    await db.close()


async def update_birthday(user_id, birthday_id, name, day, month):
    db = await aiosqlite.connect("birthdays.db")

    await db.execute(
        """
        UPDATE birthdays
        SET name = ?, day = ?, month = ?
        WHERE id = ? AND user_id = ?
        """,
        (name, day, month, birthday_id, user_id)
    )

    await db.commit()
    await db.close()



async def reminder_was_sent(birthday_id, reminder_date):
    db = await aiosqlite.connect("birthdays.db")

    cursor = await db.execute(
        """
        SELECT id
        FROM sent_reminders
        WHERE birthday_id = ?
        AND reminder_date = ?
        """,
        (birthday_id, reminder_date)
    )

    result = await cursor.fetchone()

    await db.close()

    return result is not None


async def save_sent_reminder(birthday_id, reminder_date):
    db = await aiosqlite.connect("birthdays.db")

    await db.execute(
        """
        INSERT OR IGNORE INTO sent_reminders
        (birthday_id, reminder_date)
        VALUES (?, ?)
        """,
        (birthday_id, reminder_date)
    )

    await db.commit()
    await db.close()