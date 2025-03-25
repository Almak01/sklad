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
    try:
        logging.debug("Запрос на получение списка запчастей")
        
        cursor.execute("SELECT id, name, quantity FROM parts")
        parts = cursor.fetchall()

        if not parts:
            logging.debug("Склад пуст.")
            bot.send_message(message.chat.id, "📭 Склад пуст.")
            return

        text = "📋 Список запчастей:\n\n"  # Завершена строка
        for part in parts:
            part_id, name, quantity = part
            text += f"🔹 ID {part_id}: {name} - {quantity} шт.\n"

        logging.debug("Отправка списка запчастей")
        bot.send_message(message.chat.id, text)

    except Exception as e:
        logging.error(f"Ошибка при получении списка запчастей: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при получении списка запчастей.")

# 🔹 Обработка нажатия на кнопку "Добавить запчасть"
@bot.message_handler(func=lambda message: message.text == "➕ Добавить запчасть")
def add_part(message):
    try:
        logging.debug("Запрос на добавление запчасти.")
        bot.send_message(message.chat.id, "Введите название запчасти:")
        bot.register_next_step_handler(message, process_name)
    
    except Exception as e:
        logging.error(f"Ошибка при обработке запроса на добавление запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при добавлении запчасти.")

# 🔹 Обработка ввода названия запчасти
def process_name(message):
    try:
        name = message.text
        logging.debug(f"Добавление запчасти с названием: {name}")
        
        msg = bot.send_message(message.chat.id, "Введите количество:")
        bot.register_next_step_handler(msg, process_quantity, name)

    except Exception as e:
        logging.error(f"Ошибка при обработке названия запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при добавлении запчасти.")

# 🔹 Обработка ввода количества запчасти
def process_quantity(message, name):
    try:
        quantity = int(message.text)  # Преобразование введенного значения в целое число
        logging.debug(f"Количество для запчасти {name}: {quantity}")
        
        cursor.execute("INSERT INTO parts (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Запчасть '{name}' добавлена с количеством {quantity}.")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректное количество (целое число).")
    except Exception as e:
        logging.error(f"Ошибка при добавлении запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при добавлении запчасти.")

# 🔹 Обработка нажатия на кнопку "Выдача запчасти"
@bot.message_handler(func=lambda message: message.text == "🛠 Выдача запчасти")
def issue_part(message):
    try:
        logging.debug("Запрос на выдачу запчасти.")
        
        cursor.execute("SELECT id, name, quantity FROM parts")
        parts = cursor.fetchall()

        if not parts:
            logging.debug("Склад пуст.")
            bot.send_message(message.chat.id, "📭 Склад пуст.")
            return

        text = "📋 Список запчастей для выдачи:\n\n"
        for part in parts:
            part_id, name, quantity = part
            if quantity > 0:
                text += f"🔹 ID {part_id}: {name} - {quantity} шт.\n"

        logging.debug("Отправка списка запчастей для выдачи.")
        bot.send_message(message.chat.id, text)
        bot.send_message(message.chat.id, "Введите ID запчасти для выдачи:")

        bot.register_next_step_handler(message, process_issue_part)
    
    except Exception as e:
        logging.error(f"Ошибка при запросе на выдачу запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при выдаче запчасти.")

# 🔹 Обработка запроса на выдачу запчасти
def process_issue_part(message):
    try:
        part_id = int(message.text)
        logging.debug(f"Выдача запчасти с ID: {part_id}")
        
        cursor.execute("SELECT id, name, quantity FROM parts WHERE id = ?", (part_id,))
        part = cursor.fetchone()

        if part:
            part_id, name, quantity = part
            if quantity > 0:
                bot.send_message(message.chat.id, f"Запчасть '{name}' будет выдана. Введите ФИО получателя:")
                bot.register_next_step_handler(message, process_taken_by, part_id)
            else:
                bot.send_message(message.chat.id, "⚠ Запчасть закончилась на складе.")
        else:
            bot.send_message(message.chat.id, "❌ Запчасть с таким ID не найдена.")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректный ID запчасти.")
    except Exception as e:
        logging.error(f"Ошибка при обработке запроса на выдачу запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при выдаче запчасти.")

# 🔹 Обработка ввода ФИО получателя
def process_taken_by(message, part_id):
    try:
        taken_by = message.text
        logging.debug(f"Запчасть выдана {taken_by}")
        
        cursor.execute("SELECT name, quantity FROM parts WHERE id = ?", (part_id,))
        part = cursor.fetchone()

        if part:
            name, quantity = part
            cursor.execute("UPDATE parts SET quantity = quantity - 1 WHERE id = ?", (part_id,))
            cursor.execute("INSERT INTO transactions (part_id, quantity, taken_by, transaction_type) VALUES (?, ?, ?, 'issue')", 
                           (part_id, 1, taken_by))
            conn.commit()

            bot.send_message(message.chat.id, f"✅ Запчасть '{name}' выдана {taken_by}.")
        else:
            bot.send_message(message.chat.id, "❌ Запчасть с таким ID не найдена.")
    
    except Exception as e:
        logging.error(f"Ошибка при выдаче запчасти: {e}")
        bot.send_message(message.chat.id, "⚠ Ошибка при выдаче запчасти.")

# Запуск бота
if __name__ == "__main__":
    logging.debug("Бот готов к запуску.")
    bot.polling(none_stop=True)
