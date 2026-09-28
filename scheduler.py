from datetime import date

from database import (
    get_all_birthdays,
    reminder_was_sent,
    save_sent_reminder
)


async def check_birthdays(bot):
    today = date.today()

    birthdays = await get_all_birthdays()

    for birthday in birthdays:
        birthday_id, user_id, name, day, month = birthday

        try:
            birthday_date = date(
                today.year,
                month,
                day
            )
        except ValueError:
            continue

        if birthday_date < today:
            try:
                birthday_date = date(
                    today.year + 1,
                    month,
                    day
                )
            except ValueError:
                continue

        days_left = (
            birthday_date - today
        ).days

        if days_left not in (1, 3, 7):
            continue

        reminder_key = (
            f"{birthday_date.isoformat()}_{days_left}"
        )

        already_sent = await reminder_was_sent(
            birthday_id,
            reminder_key
        )

        if already_sent:
            continue

        await bot.send_message(
            user_id,
            f"🔔 Напоминание!\n\n"
            f"🎂 {name} — "
            f"день рождения через "
            f"{days_left} дн."
        )

        await save_sent_reminder(
            birthday_id,
            reminder_key
        )