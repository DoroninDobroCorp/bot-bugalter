from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

import config
from modules.utils import gather_tables

router = Router()


# send tables from /tables/<date> by date
@router.message(Command('tables'), F.chat.type == 'private')
async def send_tables(msg: Message):
    if msg.from_user.id not in config.ALLOWED:
        return

    filters = msg.text.replace('/tables', '').strip().split(',')

    if filters[0] == '':
        await msg.answer(
            "```\n"
            "Вывод таблиц с репортами\n\n"
            "Фильтры:\n"
            "date - дата (day.month.year)\n"
            "from - дата от (day.month.year)\n" \
            "to - дата до (day.month.year)\n"
            "status - статус (Обычный, Основной)\n"
            "source - источник\n"
            "country - страна\n"
            "bookmaker - БК (шаблон)\n"
            "profile - профиль БК\n"
            "error - ошибка (0 - нет, 1 - да)\n"
            "over - перебор (0 - нет, 1 - да)\n\n"
            "/tables all\n"
            "/tables date=01.01.2024, status=Обычный, error=1\n" \
            "/tables from=01.01.2024, to=01.02.2025"
            "\n```"
        )

    else:
        await gather_tables([f.strip() for f in filters])

        await msg.answer_document(
            document=FSInputFile("tables/main_table.xlsx"),
            caption="Таблица бугалтерии"
        )

        await msg.answer_document(
            document=FSInputFile("tables/bot_table.xlsx"),
            caption="Таблица для бота"
        )
