from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import CommandObject, Command

from modules.models import Report
import datetime

router = Router()


@router.message(Command(commands=["allowed"]))
async def allowed_handler(message: Message, command: CommandObject):
    if message.text == "/allowed":
        await message.answer(
            "Пожалуйста, укажите название профиля после команды /allowed")
        return

    profile = command.args
    if not profile.startswith("Any") or " " in profile:
        await message.answer(
            "Некорректный формат профиля\nПрофиль должен начинаться с 'Any' и не содержать пробелов")
        return

    reports = [r for r in await Report.all() if r.bookmaker.name == profile]

    total_limit = 1800
    total_bet = 0

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    from_ = now - datetime.timedelta(hours=24, minutes=-30)
    first_bet_time = None
    first_bet_amount = None

    for report in reports:
        try:
            dt = datetime.datetime.strptime(report.date,
                                            "%d.%m.%Y %H:%M:%S").replace(
                tzinfo=datetime.timezone.utc)
        except:
            dt = datetime.datetime.strptime(report.date, "%d.%m.%Y").replace(
                tzinfo=datetime.timezone.utc)

        if dt >= from_:
            amount = float(report.bet_amount)
            total_bet += amount
            if not first_bet_time:
                first_bet_time = dt
                first_bet_amount = amount

    remaining = total_limit - total_bet

    response = f"Профиль: {profile}\n"
    response += f"Общий лимит: {total_limit}\n"
    response += f"Проставлено за последние 24 часа: {total_bet}\n"
    response += f"Осталось доступно для проставления: {round(remaining, 2)}\n\n"

    if first_bet_time:
        time_diff = (now - first_bet_time + datetime.timedelta(
            hours=24)).total_seconds()
        hours, minutes = divmod(time_diff, 3600)
        hours = int(hours)
        minutes = int(minutes / 60)
        response += f"Лимит освободится через {hours}:{minutes}\nБудет доступно {round(remaining + first_bet_amount, 2)}"
    else:
        response += "За последние 24 часа ставок не было"

    await message.answer(response, parse_mode=ParseMode.HTML)
