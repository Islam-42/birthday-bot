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

        # Напоминания за 7, 3 и 1 день
        if days_left in (1, 3, 7):

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

        # Напоминание в сам день рождения
        elif days_left == 0:

            reminder_key = (
                f"{birthday_date.isoformat()}_today"
            )

            already_sent = await reminder_was_sent(
                birthday_id,
                reminder_key
            )

            if already_sent:
                continue

            await bot.send_message(
                user_id,
                f"🎉 Сегодня день рождения!\n\n"
                f"🎂 У {name} сегодня день рождения!\n"
                f"Не забудь поздравить! 🥳"
            )

            await save_sent_reminder(
                birthday_id,
                reminder_key
            )