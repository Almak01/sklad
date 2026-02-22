from datetime import datetime
import telebot
from telebot.types import BusinessMessagesDeleted

BOT_TOKEN = "8480414614:AAEOuau7qDP1ttNOvbVDgXfzkQJvKDZmGF4"  # СЮДА_ВСТАВЬ_ТОКЕН_БОТА
OWNER_ID = 682539696  # СЮДА_ВСТАВЬ_ТВОЙ_АЙДИ

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

MESSAGES = {}

def chat_name(chat):
    return chat.title or f"{chat.first_name or ''} {chat.last_name or ''}".strip()

def is_view_once(msg):
    return bool(getattr(msg, "self_destruct_type", None) or getattr(msg, "has_media_spoiler", False))

def base_record(msg):
    return {
        "from_user": msg.from_user.first_name,
        "from_user_id": msg.from_user.id,
        "type": msg.content_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

def _photo(msg): return msg.photo[-1].file_id
def _video(msg): return msg.video.file_id
def _video_note(msg): return msg.video_note.file_id
def _voice(msg): return msg.voice.file_id
def _audio(msg): return msg.audio.file_id
def _animation(msg): return msg.animation.file_id
def _sticker(msg): return msg.sticker.file_id
def _document(msg): return msg.document.file_id

MEDIA_EXTRACTORS = {
    "photo": _photo,
    "video": _video,
    "video_note": _video_note,
    "voice": _voice,
    "audio": _audio,
    "animation": _animation,
    "sticker": _sticker,
    "document": _document,
}

SEND_WITH_CAPTION = {
    "photo": bot.send_photo,
    "video": bot.send_video,
    "audio": bot.send_audio,
    "animation": bot.send_video,
    "document": bot.send_document,
}

@bot.business_message_handler(content_types=[
    "text", "photo", "video", "video_note", "document",
    "voice", "audio", "animation", "sticker", "location", "contact"
])
def on_business_message(msg):
    key = (msg.chat.id, msg.message_id)
    record = base_record(msg)

    if msg.content_type == "text":
        record["content"] = msg.text
        MESSAGES[key] = record
        return

    if msg.content_type == "location":
        record["content"] = f"[location] lat={msg.location.latitude}, lon={msg.location.longitude}"
        MESSAGES[key] = record
        return

    if msg.content_type == "contact":
        record["content"] = f"[contact] {msg.contact.first_name} {msg.contact.last_name or ''}, tel={msg.contact.phone_number}"
        MESSAGES[key] = record
        return

    extractor = MEDIA_EXTRACTORS.get(msg.content_type)
    if extractor:
        record["file_id"] = extractor(msg)
        MESSAGES[key] = record
        if is_view_once(msg):
            bot.send_message(OWNER_ID, "Одноразовое медиа сохранено")

@bot.edited_business_message_handler(content_types=["text"])
def on_edit(msg):
    key = (msg.chat.id, msg.message_id)
    old = MESSAGES.get(key)
    MESSAGES[key] = {"type": "text", "content": msg.text}
    if old:
        bot.send_message(
            OWNER_ID,
            f"<b>Сообщение отредактировано</b>\n"
            f"Чат: {chat_name(msg.chat)}\n\n"
            f"<b>Было:</b>\n{old.get('content')}\n\n"
            f"<b>Стало:</b>\n{msg.text}"
        )

@bot.deleted_business_messages_handler()
def on_delete(event: BusinessMessagesDeleted):
    chat = event.chat

    for msg_id in event.message_ids:
        key = (chat.id, msg_id)
        record = MESSAGES.pop(key, None)
        if not record:
            continue

        msg_text = (
            f"<b>Сообщение удалено</b>\n"
            f"Чат: {chat_name(chat)}\n"
            f"От: {record.get('from_user')}\n"
            f"Тип: {record.get('type')}"
        )

        if record.get("type") == "text" and "content" in record:
            msg_text += f"\n\n<b>Текст:</b> {record['content']}"

        file_id = record.get("file_id")
        msg_type = record.get("type")

        if msg_type == "video_note" and file_id:
            bot.send_video_note(OWNER_ID, file_id)
            bot.send_message(OWNER_ID, msg_text)
            continue

        if msg_type == "sticker" and file_id:
            bot.send_sticker(OWNER_ID, file_id)
            bot.send_message(OWNER_ID, msg_text)
            continue

        if msg_type == "voice" and file_id:
            bot.send_voice(OWNER_ID, file_id)
            bot.send_message(OWNER_ID, msg_text)
            continue

        if file_id and msg_type in SEND_WITH_CAPTION:
            SEND_WITH_CAPTION[msg_type](OWNER_ID, file_id, caption=msg_text)
        else:
            bot.send_message(OWNER_ID, msg_text)

print("Бот запущен")
bot.infinity_polling()
