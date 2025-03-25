import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import os

TOKEN = os.getenv("BOT_TOKEN")  # Загружаем токен из переменных окружения

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Подключаем базу данных
conn = sqlite3.connect("parts.db")
cursor = conn.cursor()

# Создаем таблицу (если её нет)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    )
""")
conn.commit()

# Кнопки меню
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("➕ Добавить запчасть"), KeyboardButton("📦 Список запчастей"))

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Добро пожаловать в систему склада запчастей!", reply_markup=kb)

# Добавление запчасти
@dp.message_handler(lambda message: message.text == "➕ Добавить запчасть")
async def add_part(message: types.Message):
    await message.answer("Введите название запчасти и количество (пример: Фильтр 5)")

@dp.message_handler()
async def process_part(message: types.Message):
    try:
        name, quantity = message.text.rsplit(" ", 1)
        quantity = int(quantity)

        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()

        await message.answer(f"✅ Добавлена запчасть: {name}, {quantity} шт.")
    except:
        await message.answer("⚠ Ошибка! Введите данные в формате: `Название Количество`")

# Вывод списка запчастей
@dp.message_handler(lambda message: message.text == "📦 Список запчастей")
async def list_parts(message: types.Message):
    cursor.execute("SELECT name, quantity FROM parts")
    parts = cursor.fetchall()

    if not parts:
        await message.answer("Склад пуст.")
        return

    text = "📋 Список запчастей:\n\n"
    for name, quantity in parts:
        text += f"🔹 {name}: {quantity} шт.\n"

    await message.answer(text)

# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
