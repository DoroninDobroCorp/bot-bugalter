from data.config import async_engine
from data.base import Model
from data.tools import session_scope
from data.models import *
from sqlalchemy import select
from functools import wraps
from aiogram import types
from data.utils import *


async def on_startup(dp):
    # Create tables in db
    async with async_engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


async def on_shutdown(dp):
    # Close db connection (if used)
    await dp.storage.close()
    await dp.storage.wait_closed()


def admin_required(handler):
    """Decorator for admin only commands."""

    @wraps(handler)
    async def wrapper(message: types.Message, *args, **kwargs):
        if not await is_admin(message.from_user.id):
            await message.answer("You are not an admin!")
            return
        return await handler(message, *args, **kwargs)

    return wrapper


def employee_required(handler):
    """Decorator for employee only commands."""

    @wraps(handler)
    async def wrapper(message: types.Message, *args, **kwargs):
        if not await if_user_employee(message.from_user.id):
            await message.answer("You are not employee!")
            return
        return await handler(message, *args, **kwargs)

    return wrapper


"""функция для проверки строки на то что она является числом"""


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


async def format_report_stats(reports):
    keyboard = types.InlineKeyboardMarkup()

    for i, report in enumerate(reports, start=1):
        button_text = f"Отчет № {report.id} {'🔴' if report.is_error else '🟢'} ({report.real_profit:.2f} €)"
        button_data = f"report_details_|_{report.id}"
        keyboard.add(types.InlineKeyboardButton(text=button_text,
                                                callback_data=button_data))

    return keyboard


async def pay_all_salaries(message: types.Message):
    employees = await get_employees()
    for employee in employees:
        empl_balance = await employee.get_balance()
        if empl_balance > 0:
            await pay_employee_salary(employee.id)
            await message.bot.send_message(employee.id,
                                           f"Вам была выплачена зарплата в размере {empl_balance:.2f} EUR.")
