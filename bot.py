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
conn.commit()

# 🔹 Главное меню с кнопками
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    add_button = types.KeyboardButton("➕ Добавить запчасть")
    list_button = types.KeyboardButton("📦 Список запчастей")
    markup.add(add_button, list_button)

    bot.send_message(message.chat.id, "Привет! Это бот склада запчастей. \n"
                                      "Выберите одну из опций ниже:", reply_markup=markup)

# 🔹 Обработка нажатия на кнопку "Добавить запчасть"
@bot.message_handler(func=lambda message: message.text == "➕ Добавить запчасть")
def add_part(message):
    msg = bot.send_message(message.chat.id, "Введите название запчасти и количество через пробел (например: Фильтр 5):")
    bot.register_next_step_handler(msg, process_add_part)

# 🔹 Обработка текста для добавления запчасти
def process_add_part(message):
    try:
        name, quantity = message.text.split(" ", 1)
        quantity = int(quantity)

        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Добавлена запчасть: {name}, {quantity} шт.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠ Ошибка! Используйте формат:\n`[название] [количество]`")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка: {e}")

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
