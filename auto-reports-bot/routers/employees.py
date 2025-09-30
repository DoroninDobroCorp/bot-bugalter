from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

import config

from modules.models import Employee
from modules.logs import info


router = Router()


# list of employees and add/del commands
@router.message(Command('employees'), F.chat.type == 'private')
async def list_employees(msg: Message):
	if msg.from_user.id not in config.ALLOWED:
		return

	text = "Сотрудники:\n"
	employees = [empl for empl in await Employee.all() if empl.second_name]

	for i, employee in enumerate(employees):
		text += f"{i+1}\\. `{employee.second_name}`\n"

	await msg.answer(text)


# add employee by id
@router.message(Command('empl'), F.chat.type == 'private')
async def add_employee(msg: Message):
	if msg.from_user.id not in config.ALLOWED:
		return

	name_id = msg.text.split()[1:]
	name = name_id[0]
	user_id = int(name_id[1])

	employee = await Employee.get(id=user_id)

	if not employee:
		await info(msg, f"Сотрудник с id {user_id} не добавлен в Бухалтерии")
		return

	await employee.update(second_name=name)
	await msg.answer("Имя сотрудника обновленно")

