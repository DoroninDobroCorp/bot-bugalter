from aiogram.enums import ParseMode
from aiogram.types import (
	Message,
	ReactionTypeEmoji as Reaction
)

from config import bot
import config
from modules.models import Report


async def react_to(msg: Message, emoji: str):
    try:
        await msg.react([Reaction(emoji=emoji)])
    except Exception:
        # Ignore reaction failures (e.g., reactions disabled or insufficient rights)
        pass


async def created(msg: Message):
    await react_to(msg, '👍')

    text = (
        f"Отчёт создан в `{msg.chat.title}`\n"
        "```\n"
        f"{msg.caption or msg.text}"
        "\n```"
    )
    for user_id in config.ALLOWED:
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except Exception:
            continue


async def edited(msg: Message):
    await react_to(msg, '👍')

    for user_id in config.ALLOWED:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"Отчёт отредактирован в `{msg.chat.title}`\n"
                    "```\n"
                    f"{msg.caption or msg.text}"
                    "\n```"
                )
            )
        except Exception:
            continue


async def deleted(msg: Message):
    for user_id in config.ALLOWED:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"Отчёт удалён в `{msg.chat.title}`\n"
                    "```\n"
                    f"{msg.caption or msg.text}"
                    "\n```"
                )
            )
        except Exception:
            continue


async def incorrect(msg: Message, error: Exception):
    await react_to(msg, '👎')

    for user_id in config.ALLOWED:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"Неправильный отчёт в `{msg.chat.title}`\n"
                    "```\n"
                    f"{msg.caption or msg.text}"
                    "\n```"
                    "```\n"
                    f"{error}"
                    "\n```"
                )
            )
        except Exception:
            continue


async def error(report: Report, error: Exception):
    for user_id in config.ALLOWED:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "Не удалось выгрузить отчёт\n"
                    "```\n"
                    f"{report.country.name} {report.bookmaker.name}\n"
                    f"{report.bookmaker.bk_name} {report.bet_amount} {report.coefficient}\n"
                    f"{', '.join(report.employees)}\n"
                    "\n```"
                    "```\n"
                    f"{error}"
                    "\n```"
                )
            )
        except Exception:
            continue


async def info(msg: Message, text: str):
	for user_id in config.ALLOWED:
		await bot.send_message(
			chat_id=user_id,
			text=(
				"```\n"
				f"{msg.caption or msg.text}"
				"\n```\n"
				"```\n"
				f"{text}"
				"\n```"
			)
		)
