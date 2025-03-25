import asyncio
import os
import logging
import sqlite3
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# Устанавливаем логирование
logging.basicConfig(level=logging.INFO)

# Токен бота (замени на свой)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Создаем базу данных
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
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    taken_by TEXT NOT NULL,
    transaction_type TEXT NOT NULL,  -- "add" или "issue"
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id)
)
""")
conn.commit()
conn.close()

# 📌 Создаем клавиатуру (не скрывается после нажатия)
main_menu = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=False,
    is_persistent=True
)

main_menu.add(
    KeyboardButton("📦 Добавить запчасть"),
    KeyboardButton("📋 Список запчастей"),
    KeyboardButton("🔻 Выдача запчасти"),
    KeyboardButton("📊 Отчет")
)

# 📌 Обработчик команды /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🔧 Добро пожаловать! Выберите действие:", reply_markup=main_menu)

# 📌 Добавление запчасти
@dp.message_handler(lambda message: message.text == "📦 Добавить запчасть")
async def add_part(message: types.Message):
    await message.answer("Введите название запчасти:")
    dp.register_message_handler(get_part_name, state="add_part_name")

async def get_part_name(message: types.Message):
    part_name = message.text
    await message.answer("Введите количество:")
    dp.register_message_handler(lambda msg: save_part(msg, part_name), state="add_part_quantity")

async def save_part(message: types.Message, part_name):
    try:
        quantity = int(message.text)
        conn = sqlite3.connect("parts.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (part_name, quantity))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Добавлена запчасть: {part_name} (кол-во: {quantity})", reply_markup=main_menu)
    except ValueError:
        await message.answer("❌ Введите корректное число.")

# 📌 Вывод списка запчастей
@dp.message_handler(lambda message: message.text == "📋 Список запчастей")
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

# 📌 Выдача запчасти
@dp.message_handler(lambda message: message.text == "🔻 Выдача запчасти")
async def issue_part(message: types.Message):
    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity FROM parts WHERE quantity > 0")
    parts = cursor.fetchall()
    conn.close()

    if not parts:
        await message.answer("📭 Нет доступных запчастей.")
        return

    text = "📋 Выберите номер запчасти для выдачи:\n"
    for part in parts:
        text += f"{part[0]}. {part[1]} — {part[2]} шт.\n"

    await message.answer(text)
    dp.register_message_handler(get_issue_part, state="issue_part_id")

async def get_issue_part(message: types.Message):
    try:
        part_id = int(message.text)
        await message.answer("Введите количество для выдачи:")
        dp.register_message_handler(lambda msg: get_issue_quantity(msg, part_id), state="issue_quantity")
    except ValueError:
        await message.answer("❌ Введите корректный номер запчасти.")

async def get_issue_quantity(message: types.Message, part_id):
    try:
        quantity = int(message.text)
        await message.answer("Введите ФИО получателя:")
        dp.register_message_handler(lambda msg: confirm_issue(msg, part_id, quantity), state="issue_person")
    except ValueError:
        await message.answer("❌ Введите корректное число.")

async def confirm_issue(message: types.Message, part_id, quantity):
    taken_by = message.text
    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()

    # Проверяем наличие запчасти
    cursor.execute("SELECT name, quantity FROM parts WHERE id = ?", (part_id,))
    part = cursor.fetchone()

    if not part or part[1] < quantity:
        await message.answer("❌ Недостаточно запчастей на складе.")
        conn.close()
        return

    # Обновляем количество
    new_quantity = part[1] - quantity
    cursor.execute("UPDATE parts SET quantity = ? WHERE id = ?", (new_quantity, part_id))

    # Записываем транзакцию
    cursor.execute("INSERT INTO transactions (part_id, quantity, taken_by, transaction_type) VALUES (?, ?, ?, 'issue')",
                   (part_id, quantity, taken_by))

    conn.commit()
    conn.close()

    await message.answer(f"✅ Выдано {quantity} шт. {part[0]} получателю: {taken_by}", reply_markup=main_menu)

# 📌 Отчет в Excel
@dp.message_handler(lambda message: message.text == "📊 Отчет")
async def generate_report(message: types.Message):
    conn = sqlite3.connect("parts.db")
    cursor = conn.cursor()

    # Получаем данные за текущий месяц
    current_month = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT p.name, t.quantity, t.taken_by, t.date
        FROM transactions t
        JOIN parts p ON t.part_id = p.id
        WHERE strftime('%Y-%m', t.date) = ?
    """, (current_month,))
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        await message.answer("📭 За этот месяц выдач не было.")
        return

    # Создаем DataFrame и сохраняем в Excel
    df = pd.DataFrame(transactions, columns=["Название", "Количество", "ФИО", "Дата"])
    file_path = "report.xlsx"
    df.to_excel(file_path, index=False)

    # Отправляем отчет
    with open(file_path, "rb") as report:
        await bot.send_document(message.chat.id, report, caption="📊 Отчет за текущий месяц")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
