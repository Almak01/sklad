import os
import telebot
from telebot import types
import sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    logging.debug("Бот запущен. Отправлено главное меню.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    add_button = types.KeyboardButton("➕ Добавить запчасть")
    list_button = types.KeyboardButton("📦 Список запчастей")
    issue_button = types.KeyboardButton("🛠 Выдача запчасти")
    report_button = types.KeyboardButton("📊 Отчет")
    markup.add(add_button, list_button, issue_button, report_button)

    bot.send_message(message.chat.id, "Привет! Это бот склада запчастей. \n"
                                      "Выберите одну из опций ниже:", reply_markup=markup)

# 🔹 Обработка нажатия на кнопку "Список запчастей"
@bot.message_handler(func=lambda message: message.text == "📦 Список запчастей")
def list_parts(message):
