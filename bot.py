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


bot = Bot(token=TOKEN)
dp = Dispatcher()


class BirthdayForm(StatesGroup):
    # Добавление
    name = State()
    date = State()

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
    await state.set_state(BirthdayForm.name)

    await message.answer(
        "Как зовут человека?"
    )


@dp.message(lambda message: message.text == "🎂 Добавить")
async def add_button_handler(
    message: Message,
    state: FSMContext
):
    await state.set_state(BirthdayForm.name)

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

    await state.set_state(BirthdayForm.date)

    await message.answer(
        "Введи дату рождения в формате ДД.ММ\n"
        "Например: 15.10"
    )


@dp.message(BirthdayForm.date)
async def get_date(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    name = data["name"]
    date_text = message.text

    try:
        day, month = map(
            int,
            date_text.split(".")
        )

        if not (
            1 <= day <= 31
            and
            1 <= month <= 12
        ):
            raise ValueError

        # Проверяем, существует ли такая дата
        datetime(
            2000,
            month,
            day
        )

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n\n"
            "Используй формат ДД.ММ\n"
            "Например: 15.10"
        )
        return

    await add_birthday(
        message.from_user.id,
        name,
        day,
        month
    )

    await message.answer(
        f"✅ Сохранил!\n\n"
        f"🎂 {name} — {day:02d}.{month:02d}",
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# СПИСОК
# =========================

@dp.message(Command("list"))
async def list_birthdays(message: Message):
    await show_birthdays(message)


@dp.message(lambda message: message.text == "📋 Мои дни рождения")
async def list_button_handler(message: Message):
    await show_birthdays(message)


async def show_birthdays(message: Message):
    birthdays = await get_birthdays(
        message.from_user.id
    )

    if not birthdays:
        await message.answer(
            "У тебя пока нет сохранённых дней рождения 🎂"
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
            "У тебя пока нет сохранённых дней рождения 🎂"
        )
        return

    text = (
        "🗑 Выбери номер дня рождения "
        "для удаления:\n\n"
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
        BirthdayForm.delete_choice
    )

    await message.answer(text)


@dp.message(BirthdayForm.delete_choice)
async def delete_choice_handler(
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
            "У тебя больше нет сохранённых дней рождения."
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

    birthday_id, name, day, month = birthday

    await delete_birthday(
        message.from_user.id,
        birthday_id
    )

    await message.answer(
        f"🗑 Удалил:\n\n"
        f"🎂 {name} — {day:02d}.{month:02d}",
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
            "У тебя пока нет сохранённых дней рождения 🎂"
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
            "У тебя нет сохранённых дней рождения."
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
        "Введи новую дату рождения "
        "в формате ДД.ММ\n"
        "Например: 15.10"
    )


@dp.message(BirthdayForm.edit_date)
async def edit_date_handler(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    try:
        day, month = map(
            int,
            message.text.split(".")
        )

        if not (
            1 <= day <= 31
            and
            1 <= month <= 12
        ):
            raise ValueError

        datetime(
            2000,
            month,
            day
        )

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n\n"
            "Используй формат ДД.ММ\n"
            "Например: 15.10"
        )
        return

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
async def check_handler(message: Message):
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