from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

import config

from modules.models import Source


router = Router()


# list of partners and add/del commands
@router.message(Command('partners'), F.chat.type == 'private')
async def list_employees(msg: Message):
    if msg.from_user.id not in config.ALLOWED:
        return

    text = "Партнёры:\n"
    sources = await Source.all()

    for i, source in enumerate(sources):
        text += f"{i+1}\\. `{source.name}`\n"

    await msg.answer(text)

