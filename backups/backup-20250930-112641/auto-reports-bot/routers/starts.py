from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

import config

from modules.logs import *
from modules.models import Source


router = Router()


# commands /start for private and group
@router.message(F.text == '/start 26ESVuE', F.chat.type == 'private')
async def start_private_handler(msg: Message):
    if msg.from_user.id not in config.ALLOWED:
        config.ALLOWED.append(msg.from_user.id)

    await msg.answer((
        "```\n"
        "Таблицы: /tables\n\n"

        "Список сотрудников: /employees\n"
        "Добавить/Удалить сотрудника: /employee\n\n"

        "Список источников: /partners\n"
        "Добавить/Удалить источник: /parther\n"
        "```"
    ))


@router.message(Command('help'), F.chat.type == 'private')
async def help_command(msg: Message):
    await msg.answer((
        "```\n"
        "Таблицы: /tables\n\n"

        "Список сотрудников: /employees\n"
        "Добавить сотрудника: /empl <name> <id>\n"
        "Список источников: /partners\n\n"

        "Лимит ставок на профиль: /allowed <ПРОФИЛЬ>"
        "\n```"
    ))


@router.message(Command('start'), F.chat.type.contains('group'))
async def start_group_handler(msg: Message):
    if ' ' not in msg.text:
        return

    name = msg.text.split(maxsplit=1)[1]
    source_by_id = await Source.get(chat_id=msg.chat.id, is_deleted=False)
    source_by_name = await Source.get(name=name, is_deleted=False)

    if not source_by_id:
        if not source_by_name:
            await info(msg, f"Не найден источник '{name}' (добавьте в Бухалтерии)")
            return

        await source_by_name.update(chat_id=msg.chat.id)
        await info(msg, f"Источник '{name}' привязан к '{msg.chat.title}'")

    else:
        await info(msg, f"Эта группа уже привязана к источнику '{source_by_id.name}'")


@router.message(Command('untie'), F.chat.type.contains('group'))
async def untie_source(msg: Message):
    source = await Source.get(chat_id=msg.chat.id)

    if source:
        await source.update(chat_id=0)
        await info(msg, f"Источник '{source.name}' отвязан от '{msg.chat.title}'")

    else:
        await info(msg, "К этой группе не привязан источник")


@router.message(Command('idchat'))
async def idchat_handler(msg: Message):
    """Команда для получения ID текущего чата. Работает везде: в приватных чатах и группах."""
    chat_info = f"ID этого чата: `{msg.chat.id}`"
    if msg.chat.title:
        chat_info += f"\nНазвание: {msg.chat.title}"
    chat_info += f"\nТип: {msg.chat.type}"
    await msg.reply(chat_info, parse_mode='Markdown')


# Дополнительный обработчик для текстовых команд в группах (когда бот не видит /команду)
@router.message(F.text.regexp(r'^[/!]idchat'))
async def idchat_text_handler(msg: Message):
    """Обработчик на случай если команда пришла как обычный текст"""
    await idchat_handler(msg)


@router.message(Command('logs'), F.chat.type == 'private')
async def get_logs(msg: Message):
    await msg.answer_document(
        document=FSInputFile("logs.log")
    )

    with open("logs.log", "w", encoding='utf-8') as f:
        f.write("")
