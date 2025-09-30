import asyncio
from aiogram import Bot
from config import TOKEN
async def main():
    print("TOKEN:", TOKEN)
    bot = Bot(token=TOKEN)
    me = await bot.get_me()
    print("GET_ME:", me)
    try:
        updates = await bot.get_updates(timeout=1)
        print("GET_UPDATES OK, count:", len(updates))
    except Exception as e:
        print("GET_UPDATES ERROR:", repr(e))
    await bot.session.close()
asyncio.run(main())
