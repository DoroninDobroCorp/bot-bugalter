from aiogram import Dispatcher, F, types

import sys
import asyncio

import config

from modules.tools import init_models
from modules.base import Model
from modules.parser import parse
from modules.utils import *
from modules.logs import *
import routers


bot = config.bot
dp = Dispatcher()


# when created new message with photo
@dp.message(F.photo.is_not(None), F.caption.is_not(None))
async def msg_handler(msg: types.Message):
	if not await exist_source(msg.chat.id):
		return

	report = await parse(msg)

	if isinstance(report, Exception):
		await incorrect(msg, report)
		return

	await add_report_to_db(report)
	await created(msg)


# when message edited (added profit etc.)
@dp.edited_message(F.photo.is_not(None), F.caption.is_not(None))
async def edited_handler(msg: types.Message):
	if not await exist_source(msg.chat.id):
		return

	report = await parse(msg)

	if isinstance(report, Exception):
		await incorrect(msg, report)
		return

	if report.delete:
		await delete_report(report)
		await deleted(msg)
		return

	if await exist_report(report.msg_id):
		await edit_report(report)
		await edited(msg)
		return

	await add_report_to_db(report)
	await created(msg)


@dp.message(F.text.in_(["/idchat", "/idchat@ekjgufughufbot"]))
async def idchat_command_handler(msg: types.Message):
	"""Команда для получения ID чата. Работает в группах и приватных чатах."""
	chat_info = f"ID этого чата: `{msg.chat.id}`"
	if msg.chat.title:
		chat_info += f"\nНазвание: {msg.chat.title}"
	chat_info += f"\nТип: {msg.chat.type}"
	await msg.reply(chat_info, parse_mode='Markdown')


@dp.message(F.text.in_(["/report", "/report@ekjgufughufbot"]), F.chat.type.contains('group'))
async def add_report_handler(msg: types.Message):
	if not await exist_source(msg.chat.id):
		return

	if msg.from_user.id not in config.ALLOWED:
		return

	if not msg.reply_to_message:
		return

	report = await parse(msg.reply_to_message)

	if isinstance(report, Exception):
		await incorrect(msg.reply_to_message, report)
		return

	if await exist_report(report.msg_id):
		await edit_report(report)
		await edited(msg.reply_to_message)
		return

	await add_report_to_db(report)
	await created(msg.reply_to_message)


def error_handler(name, exception, traceback):
	print("ERROR", f'[{dt.now().strftime("%d.%m.%y %H:%M:%S")}] -', f"{name}:", exception)


async def errors_handler(error: types.ErrorEvent):
	print("ERROR", f'[{dt.now().strftime("%d.%m.%y %H:%M:%S")}] -', str(error.exception))


async def main():
    sys.excepthook = error_handler
    # await init_models(Model)

    # Startup diagnostics: print token fingerprint and bot.get_me()
    try:
        token = getattr(config, 'TOKEN', 'unknown')
        token_fp = f"{token[:6]}...{token[-6:]}" if isinstance(token, str) and len(token) > 12 else token
        print("STARTUP:", f"TOKEN_FP={token_fp}")
        me = await bot.get_me()
        print("STARTUP:", f"GET_ME id={me.id} username={me.username}")
    except Exception as e:
        print("STARTUP ERROR:", repr(e))

    dp.include_routers(
        routers.start_router,
        routers.tables_router,
        routers.employees_router,
        routers.partners_router,
        routers.allowed_bet_amount_router,
    )

    await dp.start_polling(bot)


if __name__ == '__main__':
	print("Bot started!")
	asyncio.run(main())
