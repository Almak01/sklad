import asyncio
import os
import sqlite3
import logging
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования (чтобы видеть ошибки)
logging.basicConfig(level=logging.INFO)

# Токен бота (замени на свой)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Подключение к боту
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение к базе данных (если нет — создаем)
conn = sqlite3.connect("parts.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS issued_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    issued_to TEXT NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
conn.close()

# 📌 Состояния для FSM
class AddPart(StatesGroup):
    name = State()
    quantity = State()

class IssuePart(StatesGroup):
    number = State()
    quantity = State()
    issued_to = State()

# 📌 Главное меню (кнопки)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Добавить запчасть")],
        [KeyboardButton(text="📋 Список запчастей")],
        [KeyboardButton(text="🔻 Выдача запчасти")],
        [KeyboardButton(text="📊 Отчет")]
    ],
    resize_keyboard=True
)

# 📌 Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🔧 Добро пожаловать! Выберите действие:", reply_markup=main_menu)

# 📌 Добавление запчасти (запуск FSM)
@dp.message(Text("📦 Добавить запчасть"))
async def add_part_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название запчасти:")
    await state.set_state(AddPart.name)

@dp.message(AddPart.name)
async def add_part_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите количество запчастей:")
    await state.set_state(AddPart.quantity)

@dp.message(AddPart.quantity)
async def add_part_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    part_name = data["name"]
    quantity = int(message.text)

    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (part_name, quantity))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Запчасть '{part_name}' ({quantity} шт.) добавлена!", reply_markup=main_menu)
    await state.clear()

# 📌 Просмотр списка запчастей
@dp.message(Text("📋 Список запчастей"))
async def list_parts(message: types.Message):
    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity FROM parts")
    parts = cursor.fetchall()
    conn.close()

    if not parts:
        await message.answer("📭 Список запчастей пуст.")
    else:
        text = "📋 Список запчастей:\n"
        for part in parts:
            text += f"{part[0]}. {part[1]} — {part[2]} шт.\n"
        await message.answer(text, reply_markup=main_menu)

# 📌 Выдача запчасти (запуск FSM)
@dp.message(Text("🔻 Выдача запчасти"))
async def issue_part_start(message: types.Message, state: FSMContext):
    await message.answer("Введите номер запчасти для выдачи:")
    await state.set_state(IssuePart.number)

@dp.message(IssuePart.number)
async def issue_part_number(message: types.Message, state: FSMContext):
    part_id = int(message.text)

    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, quantity FROM parts WHERE id=?", (part_id,))
    part = cursor.fetchone()
    conn.close()

    if part:
        await state.update_data(number=part_id, part_name=part[0], available=part[1])
        await message.answer(f"Введите количество (в наличии {part[1]} шт.):")
        await state.set_state(IssuePart.quantity)
    else:
        await message.answer("❌ Неверный номер запчасти. Попробуйте еще раз.", reply_markup=main_menu)
        await state.clear()

@dp.message(IssuePart.quantity)
async def issue_part_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    quantity = int(message.text)

    if quantity > data["available"]:
        await message.answer("❌ Недостаточно запчастей на складе.")
        return

    await state.update_data(quantity=quantity)
    await message.answer("Введите ФИО получателя:")
    await state.set_state(IssuePart.issued_to)

@dp.message(IssuePart.issued_to)
async def issue_part_to(message: types.Message, state: FSMContext):
    data = await state.get_data()
    issued_to = message.text

    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE parts SET quantity = quantity - ? WHERE id=?", (data["quantity"], data["number"]))
    cursor.execute("INSERT INTO issued_parts (part_name, quantity, issued_to) VALUES (?, ?, ?)", 
                   (data["part_name"], data["quantity"], issued_to))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Выдано {data['quantity']} шт. {data['part_name']} — {issued_to}.", reply_markup=main_menu)
    await state.clear()

# 📌 Отчет в Excel
@dp.message(Text("📊 Отчет"))
async def generate_report(message: types.Message):
    conn = sqlite3.connect("parts.db")
    df = pd.read_sql_query("SELECT part_name, quantity, issued_to, date FROM issued_parts WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')", conn)
    conn.close()

    if df.empty:
        await message.answer("📭 В этом месяце ничего не выдавалось.")
        return

    filename = "Отчет_выдачи.xlsx"
    df.to_excel(filename, index=False)

    await message.answer_document(types.FSInputFile(filename))

# 📌 Запуск бота (aiogram 3.x)
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
