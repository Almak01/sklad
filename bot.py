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
        transaction_type TEXT NOT NULL,  -- "add" или "issue"
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
    issue_button = types.KeyboardButton("🛠 Выдача запчасти")
    markup.add(add_button, list_button, issue_button)

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
        conn.commit()  # Сохраняем изменения в базе данных

        bot.send_message(message.chat.id, f"✅ Добавлена запчасть: {name}, {quantity} шт.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите корректное количество (целое число).")

# 🔹 Обработка нажатия на кнопку "Выдача запчасти"
@bot.message_handler(func=lambda message: message.text == "🛠 Выдача запчасти")
def issue_part(message):
    # Показываем список оставшихся запчастей с номерами
    cursor.execute("SELECT id, name, quantity FROM parts")
    parts = cursor.fetchall()

    if not parts:
        bot.send_message(message.chat.id, "📭 Склад пуст.")
        return

    text = "📋 Список запчастей:\n\n"
    for part in parts:
        part_id, name, quantity = part
        text += f"🔹 ID {part_id}: {name} - {quantity} шт.\n"

    # Выводим список и спрашиваем, какой запчасти по номеру выдать
    msg = bot.send_message(message.chat.id, text + "\nВведите номер запчасти для выдачи (ID):")
    bot.register_next_step_handler(msg, process_issue_id)

# 🔹 Обработка ввода ID запчасти для выдачи
def process_issue_id(message):
    try:
        part_id = int(message.text)

        # Проверяем, есть ли такая запчасть на складе
        cursor.execute("SELECT id, name, quantity FROM parts WHERE id = ?", (part_id,))
        part = cursor.fetchone()

        if not part:
            bot.send_message(message.chat.id, "❌ Запчасть с таким ID не найдена на складе.")
            return

        part_name, current_quantity = part[1], part[2]
        msg = bot.send_message(message.chat.id, f"Вы выбрали запчасть {part_name} ({current_quantity} шт.).\nВведите количество для выдачи:")
        bot.register_next_step_handler(msg, process_issue_quantity, part_id, part_name, current_quantity)

    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите корректный номер (целое число).")

# 🔹 Обработка ввода количества запчасти для выдачи
def process_issue_quantity(message, part_id, part_name, current_quantity):
    try:
        quantity = int(message.text)

        if current_quantity < quantity:
            bot.send_message(message.chat.id, "❌ Недостаточно запчастей на складе.")
            return

        # Запрашиваем ФИО, кто забрал запчасть
        msg = bot.send_message(message.chat.id, "Введите ФИО человека, который забрал запчасть:")
        bot.register_next_step_handler(msg, process_issue_taken_by, part_id, quantity, part_name)

    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Введите корректное количество (целое число).")

# 🔹 Обработка ввода ФИО и выдача запчасти
def process_issue_taken_by(message, part_id, quantity, part_name):
    taken_by = message.text

    # Обновляем количество запчасти на складе
    cursor.execute("UPDATE parts SET quantity = quantity - ? WHERE id = ?", (quantity, part_id))
    conn.commit()  # Сохраняем изменения в базе данных

    # Сохраняем запись о выдаче
    cursor.execute("INSERT INTO transactions (part_id, quantity, taken_by, transaction_type) VALUES (?, ?, ?, ?)", 
                   (part_id, quantity, taken_by, "issue"))
    conn.commit()  # Сохраняем изменения в базе данных

    bot.send_message(message.chat.id, f"✅ Запчасть выдана: {quantity} шт. ({taken_by})")

# 🔹 Обработка нажатия на кнопку "Список запчастей"
@bot.message_handler(func=lambda message: message.text == "📦 Список запчастей")
def list_parts(message):
    cursor.execute("SELECT id, name, quantity FROM parts")
    parts = cursor.fetchall()

    if not parts:
        bot.send_message(message.chat.id, "📭 Склад пуст.")
        return

    text = "📋 Список запчастей:\n\n"
    for part in parts:
        part_id, name, quantity = part
        text += f"🔹 ID {part_id}: {name} - {quantity} шт.\n"

    bot.send_message(message.chat.id, text)

# 🔹 Запуск бота
bot.polling(none_stop=True)
