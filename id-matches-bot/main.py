from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
import asyncio
import json
from pathlib import Path

from config import TOKEN
from data.utils import *


bot = Bot(token=TOKEN)
dp = Dispatcher()

# CONSTANTS
CHATS: list = []
CHATS_FILE = Path(__file__).resolve().parent / "chats.json"
TOPICS_FILE = Path(__file__).resolve().parent / "topics.json"
TOPICS: dict[str, int] = {}


# FUNCS
def is_chat_enabled(msg: types.Message):
    global CHATS
    # Consider chat enabled if its chat_id is present in chats.json, regardless of thread/topic
    chat_key = str(msg.chat.id)
    return any(str(item).split('/')[0] == chat_key for item in CHATS)


# BOT
@dp.message(Command("init_ids"))
async def init_chat(msg: types.Message):
    global CHATS, TOPICS
    with open(CHATS_FILE, "r", encoding='utf-8') as f:
        CHATS = json.load(f)

    current_chat = f"{msg.chat.id}/{msg.message_thread_id}"

    if is_chat_enabled(msg):
        print("removed", current_chat)
        # remove all entries for this chat id to fully disable regardless of thread
        CHATS = [c for c in CHATS if str(c).split('/')[0] != str(msg.chat.id)]
        # also remove topic binding if exists
        if TOPICS_FILE.exists():
            try:
                TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
            except Exception:
                TOPICS = {}
            TOPICS.pop(str(msg.chat.id), None)
            TOPICS_FILE.write_text(json.dumps(TOPICS), encoding='utf-8')

    else:
        print("added", current_chat)
        CHATS.append(current_chat)
        # if command from a thread -> auto bind this thread for codes
        if msg.message_thread_id is not None:
            if TOPICS_FILE.exists():
                try:
                    TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
                except Exception:
                    TOPICS = {}
            TOPICS[str(msg.chat.id)] = msg.message_thread_id
            TOPICS_FILE.write_text(json.dumps(TOPICS), encoding='utf-8')
            print(f"Auto-bound topic {msg.message_thread_id} for chat {msg.chat.id}")

    with open(CHATS_FILE, "w", encoding='utf-8') as f:
        json.dump(CHATS, f)


@dp.message(Command("idchat"))
async def get_chat_id(msg: types.Message):
    """Return chat ID and thread ID (if applicable)."""
    chat_id = msg.chat.id
    thread_id = msg.message_thread_id
    is_forum = getattr(msg.chat, 'is_forum', None)
    chat_type = msg.chat.type
    
    # Debug logging
    print(f"idchat: chat_id={chat_id}, thread_id={thread_id}, is_forum={is_forum}, chat_type={chat_type}")
    
    response = f"Chat ID: `{chat_id}`"
    if thread_id is not None:
        response += f"\nThread ID: `{thread_id}`"
    else:
        response += f"\nThread ID: None \\(основной чат\\)"
    
    response += f"\nChat type: `{chat_type}`"
    if is_forum is not None:
        response += f"\nIs forum: `{is_forum}`"
    
    await msg.reply(text=response, parse_mode=ParseMode.MARKDOWN_V2)


@dp.message(Command("set_ids_topic"))
async def set_ids_topic(msg: types.Message):
    """Bind current forum topic (thread) for sending codes in this chat."""
    global TOPICS
    chat_key = str(msg.chat.id)
    
    # Debug logging
    print(f"set_ids_topic called: chat_id={msg.chat.id}, thread_id={msg.message_thread_id}, chat_type={msg.chat.type}, is_forum={getattr(msg.chat, 'is_forum', None)}")
    
    # Check if message has thread_id (means it's from a topic/thread)
    # Note: thread_id can be 1 for "General" topic in forums, or None for regular chats
    if msg.message_thread_id is not None:
        # Load existing mapping
        if TOPICS_FILE.exists():
            try:
                TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
            except Exception:
                TOPICS = {}
        # Save mapping
        TOPICS[chat_key] = msg.message_thread_id
        TOPICS_FILE.write_text(json.dumps(TOPICS), encoding='utf-8')
        print(f"Topic set: chat {chat_key} -> thread {msg.message_thread_id}")
        await msg.answer(f"✅ Топик для кодов установлен: thread_id={msg.message_thread_id}")
    else:
        # Check if it's a forum chat (even if thread_id is None, it might be General topic)
        if getattr(msg.chat, 'is_forum', False):
            # In forums, None thread_id likely means "General" topic - use 1 as default
            if TOPICS_FILE.exists():
                try:
                    TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
                except Exception:
                    TOPICS = {}
            TOPICS[chat_key] = 1  # Use 1 for General topic
            TOPICS_FILE.write_text(json.dumps(TOPICS), encoding='utf-8')
            print(f"General topic detected: chat {chat_key} -> thread 1")
            await msg.answer(f"✅ Топик для кодов установлен: thread_id=1 (General)")
        else:
            await msg.answer("❌ Команда должна быть отправлена из ветки/топика, а не из основного чата.")


@dp.message(Command("unset_ids_topic"))
async def unset_ids_topic(msg: types.Message):
    """Unbind topic mapping for this chat."""
    global TOPICS
    chat_key = str(msg.chat.id)
    if TOPICS_FILE.exists():
        try:
            TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
        except Exception:
            TOPICS = {}
    if chat_key in TOPICS:
        TOPICS.pop(chat_key)
        TOPICS_FILE.write_text(json.dumps(TOPICS), encoding='utf-8')
        await msg.answer("✅ Топик для кодов сброшен для этого чата.")
    else:
        await msg.answer("ℹ️ Для этого чата топик не был установлен.")


@dp.message(Command("show_ids_config"))
async def show_ids_config(msg: types.Message):
    """Show current topic configuration for this chat."""
    global TOPICS
    chat_key = str(msg.chat.id)
    
    if TOPICS_FILE.exists():
        try:
            TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
        except Exception:
            TOPICS = {}
    
    response = f"📋 **Конфигурация для чата {chat_key}**\n\n"
    
    # Check if chat is enabled
    if is_chat_enabled(msg):
        response += "✅ Чат включен для рассылки кодов\n"
    else:
        response += "❌ Чат отключен для рассылки кодов\n"
    
    # Check topic binding
    if chat_key in TOPICS:
        response += f"📌 Топик для кодов: {TOPICS[chat_key]}\n"
    else:
        response += "📌 Топик не установлен (коды отправляются в ответ на сообщение)\n"
    
    # Current message info
    if msg.message_thread_id:
        response += f"\n🔹 Текущая ветка: {msg.message_thread_id}"
    else:
        response += "\n🔹 Текущее сообщение из основного чата (не из ветки)"
    
    await msg.answer(response, parse_mode=None)


async def send_code_to_destination(msg: types.Message, text: str):
    """Send code either to configured topic (if forum) or reply in-place."""
    chat_key = str(msg.chat.id)
    # If mapping exists for this chat -> send to configured topic
    if chat_key in TOPICS:
        thread_id = TOPICS.get(chat_key)
        try:
            await bot.send_message(
                chat_id=msg.chat.id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                message_thread_id=thread_id
            )
        except Exception as e:
            # Если не удалось отправить в топик, отвечаем напрямую
            print(f"Failed to send to topic {thread_id}: {e}")
            await msg.reply(text=text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        # Для обычных групп или форумов без настроенного топика - просто отвечаем на сообщение
        await msg.reply(text=text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(Command("addid"), F.chat.type == "private")
async def add_match_id(msg: types.Message):
    splitted = msg.text.split(maxsplit=1)
    if len(splitted) != 2:
        return

    match_id = splitted[1]

    existing_match = await Match.get(id=match_id)
    if existing_match:
        await msg.answer(
            text=f"Матч с ID `{match_id}` уже существует",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    await Match.create(
        id=match_id,
        name="",
        is_active=False
    )

    await msg.answer(
        text=f"`{match_id}` добавлен",
        parse_mode=ParseMode.MARKDOWN_V2
    )


@dp.message(F.photo.is_not(None))
async def photo_handler(msg: types.Message):
    if not is_chat_enabled(msg):
        return

    match_id = await generate()

    await Match.create(
        id=match_id,
        name="",
        is_active=False
    )

    await send_code_to_destination(msg, text=f"`{match_id}`")

@dp.message(F.text.is_not(None))
async def text_handler(msg: types.Message):
    if not is_chat_enabled(msg):
        return

    if msg.text.lower() not in ["лайв", "прематч"]:
        return

    match_id = await generate()

    await Match.create(
        id=match_id,
        name="",
        is_active=False
    )

    await send_code_to_destination(msg, text=f"`{match_id}`")

async def main():
	global CHATS
	with open(CHATS_FILE, "r", encoding='utf-8') as f:
		CHATS = json.load(f)

	# Load topics mapping (if exists)
	global TOPICS
	if TOPICS_FILE.exists():
		try:
			TOPICS = json.loads(TOPICS_FILE.read_text(encoding='utf-8'))
		except Exception:
			TOPICS = {}

	print("Bot started! (match-ids-bot)")
	await dp.start_polling(bot)


if __name__ == '__main__':
	asyncio.run(main())
