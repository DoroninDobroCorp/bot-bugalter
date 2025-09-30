from aiogram import Bot
from aiogram.enums import ParseMode

import sqlite3 as sql
from typing import Optional
from pathlib import Path


TOKEN = "6842489166:AAFFLbZeyCTDlBOOC_mhx0Y0vnUSHMazIFY"
bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN_V2)

ALLOWED = [1004461367, 447050022]


CONNECTS_PATH = (Path(__file__).resolve().parent / "connects.db").as_posix()
db = sql.connect(CONNECTS_PATH)
cursor = db.cursor()


# to work with sqlite3 db
def execute(query: str, res=True) -> Optional[str]:
	if res:
		result = cursor.execute(query).fetchone()
	else:
		result = cursor.execute(query).fetchall()

	db.commit()
	return result[0] if res and result else result


# init database
execute("""CREATE TABLE IF NOT EXISTS reports(
	msg_id TEXT,
	report_id INT
)""")

# execute("""CREATE TABLE IF NOT EXISTS employees(
# 	name TEXT,
# 	id INT
# )""")
