from sqlalchemy import create_engine
from modules.models import *
from sqlalchemy.orm import sessionmaker
import sqlite3 as sql

import random as rd
from string import ascii_letters, digits
from datetime import datetime as dt
import asyncio

to_engine = create_engine("sqlite:///../main.db")
Model.metadata.create_all(to_engine)
to_session = sessionmaker(bind=to_engine)()

from_db = sql.connect("database.db").cursor().execute
connects = sql.connect("connects.db").cursor().execute


# EMPLOYEES
async def import_employees():
	for employee in from_db("SELECT * FROM employees").fetchall():
		empl = await Employee.get(id=employee[0])

		if not empl:
			continue

		await empl.update(second_name=employee[1])

asyncio.run(import_employees())
to_session.commit()
