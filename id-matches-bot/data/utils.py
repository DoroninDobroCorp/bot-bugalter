from data.models import *
import random as rd
from string import (
	ascii_letters, digits
)


async def generate(length=10) -> str:
	while True:
		match_id = ''.join([
			rd.choice(ascii_letters + digits)
			for _ in range(length)
		])

		exist = await Match.get(
			id=match_id
		)

		if not exist:
			return match_id


async def get_emloyee_with_reports(employee_id: int) -> Employee|None:
	employee = await Employee.get(
		id=employee_id
	)

	if not employee:
		return None


