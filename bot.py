import os
import telebot
import sqlite3

# 🔹 Загружаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана!")

print(f"🔍 BOT_TOKEN = {BOT_TOKEN}")
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

# 🔹 Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Это бот склада запчастей. \n"
                                      "Вы можете добавлять и просматривать запчасти.\n\n"
                                      "📌 Команды:\n"
                                      "➕ /add [название] [количество] — добавить запчасть\n"
                                      "📦 /list — показать все запчасти")

# 🔹 Добавление запчасти: /add Фильтр 5
@bot.message_handler(commands=['add'])
def add_part(message):
    try:
        _, name, quantity = message.text.split(" ", 2)
        quantity = int(quantity)

        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Добавлена запчасть: {name}, {quantity} шт.")
    except:
        bot.send_message(message.chat.id, "⚠ Ошибка! Используйте формат:\n"
                                          "`/add [название] [количество]`", parse_mode="Markdown")

# 🔹 Вывод списка запчастей
@bot.message_handler(commands=['list'])
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
