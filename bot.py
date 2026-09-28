import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import (
    init_db,
    add_birthday,
    get_birthdays,
    delete_birthday,
    update_birthday
)

from scheduler import check_birthdays
from keyboards import main_keyboard

import os


TOKEN = os.getenv("BOT_TOKEN")


# =========================
# МЕСЯЦЫ
# =========================

MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,

    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,

    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "сент": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}


# =========================
# РАСПОЗНАВАНИЕ ДАТЫ
# =========================

def parse_birthday_date(date_text):
    date_text = date_text.strip().lower()

    # Формат ДД.ММ
    if "." in date_text:
        try:
            day, month = map(
                int,
                date_text.split(".")
            )

            datetime(
                2000,
                month,
                day
            )

            return day, month

        except (ValueError, TypeError):
            return None

    # Формат ДД месяц
    parts = date_text.split()

    if len(parts) == 2:
        try:
            day = int(parts[0])
        except ValueError:
            return None

        month = MONTHS.get(parts[1])

        if month is None:
            return None

        try:
            datetime(
                2000,
                month,
                day
            )
        except ValueError:
            return None

        return day, month

    return None


bot = Bot(token=TOKEN)
dp = Dispatcher()


# =========================
# СОСТОЯНИЯ
# =========================

class BirthdayForm(StatesGroup):

    # Добавление
    name = State()
    date = State()

    # Массовая загрузка
    import_list = State()

    # Редактирование
    edit_choice = State()
    edit_name = State()
    edit_date = State()

    # Удаление
    delete_choice = State()


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет! 👋\n\n"
        "Я бот-напоминалка о днях рождения.\n\n"
        "Выбери действие 👇",
        reply_markup=main_keyboard
    )


# =========================
# ДОБАВЛЕНИЕ
# =========================

@dp.message(Command("add"))
async def add_birthday_handler(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        BirthdayForm.name
    )

    await message.answer(
        "Как зовут человека?"
    )


@dp.message(lambda message: message.text == "🎂 Добавить")
async def add_button_handler(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        BirthdayForm.name
    )

    await message.answer(
        "Как зовут человека?"
    )


@dp.message(BirthdayForm.name)
async def get_name(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        name=message.text
    )

    await state.set_state(
        BirthdayForm.date
    )

    await message.answer(
        "Введи дату рождения.\n\n"
        "Можно написать:\n"
        "• 15.10\n"
        "• 15 октября\n"
        "• 5 января"
    )


@dp.message(BirthdayForm.date)
async def get_date(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    name = data["name"]
    date_text = message.text

    parsed_date = parse_birthday_date(
        date_text
    )

    if parsed_date is None:
        await message.answer(
            "❌ Неверная дата.\n\n"
            "Можно написать:\n"
            "• 15.10\n"
            "• 15 октября\n"
            "• 5 января"
        )
        return

    day, month = parsed_date

    await add_birthday(
        message.from_user.id,
        name,
        day,
        month
    )

    await message.answer(
        f"✅ Сохранил!\n\n"
        f"🎂 {name} — "
        f"{day:02d}.{month:02d}",
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# МАССОВАЯ ЗАГРУЗКА
# =========================

@dp.message(Command("import"))
async def import_command(
    message: Message,
    state: FSMContext
):
    await start_import(
        message,
        state
    )


@dp.message(lambda message: message.text == "📥 Загрузить список")
async def import_button_handler(
    message: Message,
    state: FSMContext
):
    await start_import(
        message,
        state
    )


async def start_import(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        BirthdayForm.import_list
    )

    await message.answer(
        "📥 Отправь список дней рождения.\n\n"
        "Каждый человек — с новой строки:\n\n"
        "Адам — 12.03\n"
        "Магомед — 25 июля\n"
        "Иса — 1 января\n"
        "Хасан — 18 ноября\n\n"
        "Можно использовать —, – или - "
        "между именем и датой."
    )


@dp.message(BirthdayForm.import_list)
async def import_list_handler(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "❌ Отправь список обычным текстом."
        )
        return

    lines = message.text.strip().splitlines()

    added = []
    errors = []

    for line_number, line in enumerate(
        lines,
        start=1
    ):
        line = line.strip()

        if not line:
            continue

        # Поддерживаем разные тире
        line = line.replace(
            "–",
            "—"
        ).replace(
            "-",
            "—"
        )

        if "—" not in line:
            errors.append(
                f"Строка {line_number}: "
                f"не найден разделитель"
            )
            continue

        name, date_text = line.split(
            "—",
            1
        )

        name = name.strip()
        date_text = date_text.strip()

        if not name:
            errors.append(
                f"Строка {line_number}: "
                f"не указано имя"
            )
            continue

        parsed_date = parse_birthday_date(
            date_text
        )

        if parsed_date is None:
            errors.append(
                f"Строка {line_number}: "
                f"неверная дата «{date_text}»"
            )
            continue

        day, month = parsed_date

        await add_birthday(
            message.from_user.id,
            name,
            day,
            month
        )

        added.append(
            f"🎂 {name} — "
            f"{day:02d}.{month:02d}"
        )

    result = (
        f"📥 Загрузка завершена!\n\n"
        f"✅ Добавлено: {len(added)}"
    )

    if errors:
        result += (
            f"\n❌ Ошибок: {len(errors)}\n\n"
            f"Ошибки:\n"
            + "\n".join(errors[:20])
        )

    if added:
        result += (
            "\n\nДобавленные дни рождения:\n"
            + "\n".join(added[:30])
        )

    if len(added) > 30:
        result += (
            f"\n\n...и ещё "
            f"{len(added) - 30}"
        )

    await message.answer(
        result,
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# СПИСОК
# =========================

@dp.message(Command("list"))
async def list_birthdays(
    message: Message
):
    await show_birthdays(message)


@dp.message(lambda message: message.text == "📋 Мои дни рождения")
async def list_button_handler(
    message: Message
):
    await show_birthdays(message)


async def show_birthdays(
    message: Message
):
    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя пока нет сохранённых "
            "дней рождения 🎂"
        )
        return

    text = "🎂 Твои дни рождения:\n\n"

    for index, birthday in enumerate(
        birthdays,
        start=1
    ):
        birthday_id, name, day, month = birthday

        text += (
            f"{index}. "
            f"{name} — "
            f"{day:02d}.{month:02d}\n"
        )

    await message.answer(text)


# =========================
# УДАЛЕНИЕ
# =========================

@dp.message(Command("delete"))
async def delete_command(
    message: Message,
    state: FSMContext
):
    await start_delete(
        message,
        state
    )


@dp.message(lambda message: message.text == "🗑 Удалить")
async def delete_button_handler(
    message: Message,
    state: FSMContext
):
    await start_delete(
        message,
        state
    )


async def start_delete(
    message: Message,
    state: FSMContext
):
    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя пока нет сохранённых "
            "дней рождения 🎂"
        )
        return

    text = (
        "🗑 Выбери дни рождения для удаления:\n\n"
    )

    for index, birthday in enumerate(
        birthdays,
        start=1
    ):
        birthday_id, name, day, month = birthday

        text += (
            f"{index}. "
            f"{name} — "
            f"{day:02d}.{month:02d}\n"
        )

    text += (
        "\nМожно написать:\n"
        "• 2 — удалить один\n"
        "• 1 3 5 — удалить несколько\n"
        "• 1-5 — удалить диапазон\n"
        "• все — удалить все дни рождения"
    )

    await state.set_state(
        BirthdayForm.delete_choice
    )

    await message.answer(text)


@dp.message(BirthdayForm.delete_choice)
async def delete_choice_handler(
    message: Message,
    state: FSMContext
):
    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя нет сохранённых "
            "дней рождения."
        )

        await state.clear()
        return

    user_input = message.text.strip().lower()

    # =========================
    # УДАЛИТЬ ВСЕ
    # =========================

    if user_input in (
        "все",
        "всё",
        "удалить все",
        "удалить всё"
    ):
        for birthday in birthdays:
            birthday_id, name, day, month = birthday

            await delete_birthday(
                message.from_user.id,
                birthday_id
            )

        await message.answer(
            f"🗑 Удалил все дни рождения.\n\n"
            f"Удалено: {len(birthdays)}",
            reply_markup=main_keyboard
        )

        await state.clear()
        return

    # =========================
    # РАЗБОР НОМЕРОВ
    # =========================

    numbers = set()

    parts = (
        user_input
        .replace(",", " ")
        .split()
    )

    for part in parts:

        # Диапазон: 1-5
        if "-" in part:
            try:
                start, end = map(
                    int,
                    part.split("-", 1)
                )

                if start > end:
                    start, end = end, start

                for number in range(
                    start,
                    end + 1
                ):
                    numbers.add(number)

            except ValueError:
                await message.answer(
                    f"❌ Не понял: {part}\n\n"
                    "Напиши номера, например:\n"
                    "1 3 5\n"
                    "или диапазон:\n"
                    "1-5"
                )
                return

        # Обычный номер
        else:
            try:
                numbers.add(
                    int(part)
                )

            except ValueError:
                await message.answer(
                    f"❌ Не понял: {part}\n\n"
                    "Напиши номера, например:\n"
                    "1 3 5"
                )
                return

    # =========================
    # ПРОВЕРКА НОМЕРОВ
    # =========================

    if not numbers:
        await message.answer(
            "❌ Укажи хотя бы один номер."
        )
        return

    invalid_numbers = [
        number
        for number in numbers
        if number < 1
        or number > len(birthdays)
    ]

    if invalid_numbers:
        await message.answer(
            "❌ Неверные номера: "
            + ", ".join(
                map(
                    str,
                    sorted(invalid_numbers)
                )
            )
            + "\n\n"
            f"Допустимые номера: "
            f"1–{len(birthdays)}"
        )
        return

    # =========================
    # УДАЛЕНИЕ
    # =========================

    deleted = []

    for number in sorted(numbers):
        birthday = birthdays[number - 1]

        birthday_id, name, day, month = birthday

        await delete_birthday(
            message.from_user.id,
            birthday_id
        )

        deleted.append(
            f"🎂 {name} — "
            f"{day:02d}.{month:02d}"
        )

    text = (
        f"🗑 Удалено: {len(deleted)}\n\n"
        + "\n".join(deleted)
    )

    await message.answer(
        text,
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# РЕДАКТИРОВАНИЕ
# =========================

@dp.message(Command("edit"))
async def edit_command(
    message: Message,
    state: FSMContext
):
    await start_edit(
        message,
        state
    )


@dp.message(lambda message: message.text == "✏️ Изменить")
async def edit_button_handler(
    message: Message,
    state: FSMContext
):
    await start_edit(
        message,
        state
    )


async def start_edit(
    message: Message,
    state: FSMContext
):
    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя пока нет сохранённых "
            "дней рождения 🎂"
        )
        return

    text = (
        "✏️ Выбери номер дня рождения "
        "для изменения:\n\n"
    )

    for index, birthday in enumerate(
        birthdays,
        start=1
    ):
        birthday_id, name, day, month = birthday

        text += (
            f"{index}. "
            f"{name} — "
            f"{day:02d}.{month:02d}\n"
        )

    text += "\nНапиши номер, например: 1"

    await state.set_state(
        BirthdayForm.edit_choice
    )

    await message.answer(text)


@dp.message(BirthdayForm.edit_choice)
async def edit_choice_handler(
    message: Message,
    state: FSMContext
):
    try:
        number = int(message.text)

    except ValueError:
        await message.answer(
            "❌ Введи номер из списка.\n"
            "Например: 1"
        )
        return

    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя нет сохранённых "
            "дней рождения."
        )

        await state.clear()
        return

    if number < 1 or number > len(birthdays):
        await message.answer(
            "❌ Такого номера нет.\n\n"
            "Попробуй ещё раз."
        )
        return

    birthday = birthdays[number - 1]

    birthday_id, old_name, old_day, old_month = birthday

    await state.update_data(
        birthday_id=birthday_id
    )

    await state.set_state(
        BirthdayForm.edit_name
    )

    await message.answer(
        f"✏️ Редактируем:\n\n"
        f"🎂 {old_name} — "
        f"{old_day:02d}.{old_month:02d}\n\n"
        f"Введи новое имя:"
    )


@dp.message(BirthdayForm.edit_name)
async def edit_name_handler(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        name=message.text
    )

    await state.set_state(
        BirthdayForm.edit_date
    )

    await message.answer(
        "Введи новую дату рождения.\n\n"
        "Можно написать:\n"
        "• 15.10\n"
        "• 15 октября\n"
        "• 5 января"
    )


@dp.message(BirthdayForm.edit_date)
async def edit_date_handler(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    parsed_date = parse_birthday_date(
        message.text
    )

    if parsed_date is None:
        await message.answer(
            "❌ Неверная дата.\n\n"
            "Можно написать:\n"
            "• 15.10\n"
            "• 15 октября\n"
            "• 5 января"
        )
        return

    day, month = parsed_date

    await update_birthday(
        message.from_user.id,
        data["birthday_id"],
        data["name"],
        day,
        month
    )

    await message.answer(
        f"✅ День рождения изменён!\n\n"
        f"🎂 {data['name']} — "
        f"{day:02d}.{month:02d}",
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# РУЧНАЯ ПРОВЕРКА
# =========================

@dp.message(Command("check"))
async def check_handler(
    message: Message
):
    await check_birthdays(bot)

    await message.answer(
        "✅ Проверка дней рождения выполнена."
    )


# =========================
# ЗАПУСК
# =========================

async def main():
    print("Бот запускается...")

    await init_db()

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        check_birthdays,
        "cron",
        hour=9,
        minute=0,
        args=[bot]
    )

    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())