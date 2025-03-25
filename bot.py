import os
import telebot
from telebot import types
import sqlite3

# 🔹 Загружаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана!")

bot = telebot.TeleBot(BOT_TOKEN)

# 🔹 Подключение к базе данных SQLite
conn = sqlite3.connect("parts.db", check_same_thread=False)
cursor = conn.cursor()

# 🔹 Создаем таблицу, если её нет
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
        transaction_type TEXT NOT NULL,  -- "add" или "take"
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (part_id) REFERENCES parts(id)
    )
""")
conn.commit()

# 🔹 Главное меню с кнопками
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    add_button = types.KeyboardButton("➕ Добавить запчасть")
    list_button = types.KeyboardButton("📦 Список запчастей")
    take_button = types.KeyboardButton("💼 Списать запчасть")
    markup.add(add_button, list_button, take_button)

    bot.send_message(message.chat.id, "Привет! Это бот склада запчастей. \n"
                                      "Выберите одну из опций ниже:", reply_markup=markup)

# 🔹 Обработка нажатия на кнопку "Добавить запчасть"
@bot.message_handler(func=lambda message: message.text == "➕ Добавить запчасть")
def add_part(message):
    msg = bot.send_message(message.chat.id, "Введите название запчасти:")
    bot.register_next_step_handler(msg, process_name)

# 🔹 Обработка ввода названия запчасти
def process_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "Введите количество:")
    bot.register_next_step_handler(msg, process_quantity, name)

# 🔹 Обработка ввода количества запчасти
def process_quantity(message, name):
    try:
        quantity = int(message.text)

        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Добавлена запчасть: {name}, {quantity} шт.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите корректное количество (целое число).")

# 🔹 Обработка нажатия на кнопку "Списать запчасть"
@bot.message_handler(func=lambda message: message.text == "💼 Списать запчасть")
def take_part(message):
    msg = bot.send_message(message.chat.id, "Введите название запчасти для списания:")
    bot.register_next_step_handler(msg, process_take_name)

# 🔹 Обработка ввода названия запчасти для списания
def process_take_name(message):
    part_name = message.text
    msg = bot.send_message(message.chat.id, "Введите количество для списания:")
    bot.register_next_step_handler(msg, process_take_quantity, part_name)

# 🔹 Обработка ввода количества запчасти для списания
def process_take_quantity(message, part_name):
    try:
        quantity = int(message.text)
        
        # Проверяем, есть ли такая запчасть на складе
        cursor.execute("SELECT id, quantity FROM parts WHERE name = ?", (part_name,))
        part = cursor.fetchone()

        if not part:
            bot.send_message(message.chat.id, "❌ Запчасть не найдена на складе.")
            return

        part_id, current_quantity = part
        if current_quantity < quantity:
            bot.send_message(message.chat.id, "❌ Недостаточно запчастей на складе.")
            return

        # Запрашиваем ФИО, кто забрал запчасть
        msg = bot.send_message(message.chat.id, "Введите ФИО человека, который забрал запчасть:")
        bot.register_next_step_handler(msg, process_taken_by, part_id, quantity)

    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите корректное количество (целое число).")

# 🔹 Обработка ввода ФИО и списание запчасти
def process_taken_by(message, part_id, quantity):
    taken_by = message.text

    # Обновляем количество запчасти на складе
    cursor.execute("UPDATE parts SET quantity = quantity - ? WHERE id = ?", (quantity, part_id))
    conn.commit()

    # Сохраняем запись о списании
    cursor.execute("INSERT INTO transactions (part_id, quantity, taken_by, transaction_type) VALUES (?, ?, ?, ?)", 
                   (part_id, quantity, taken_by, "take"))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Запчасть списана: {quantity} шт. ({taken_by})")

# 🔹 Обработка нажатия на кнопку "Список запчастей"
@bot.message_handler(func=lambda message: message.text == "📦 Список запчастей")
def list_parts(message):
    cursor.execute("SELECT name, quantity FROM parts")
    parts = cursor.fetchall()

    if not parts:
        bot.send_message(message.chat.id, "📭 Склад пуст.")
        return

    text = "📋 Список запчастей:\n\n"
    for name, quantity in parts:
        text += f"🔹 {name}: {quantity} шт.\n"

    bot.send_message(message.chat.id, text)

# 🔹 Запуск бота
bot.polling(none_stop=True)
