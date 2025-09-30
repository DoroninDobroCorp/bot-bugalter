import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from bot.admin import register_admin_handlers
from bot.user import register_user_handlers
from config import BOT_TOKEN
from bot.utils import on_startup, on_shutdown
from aiogram import executor
from bot.stats_admin import register_stats_handlers
from data.tools import init_models
from data.base import Model

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Register handlers
register_admin_handlers(dp)
register_stats_handlers(dp)
register_user_handlers(dp)


if __name__ == '__main__':
    print("Bot started!")
    # asyncio.run(init_models(Model))
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
