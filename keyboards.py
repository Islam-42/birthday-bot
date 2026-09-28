from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎂 Добавить"),
            KeyboardButton(text="📋 Мои дни рождения")
        ],
        [
            KeyboardButton(text="✏️ Изменить"),
            KeyboardButton(text="🗑 Удалить")
        ]
    ],
    resize_keyboard=True
)