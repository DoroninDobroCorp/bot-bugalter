from dataclasses import dataclass
from typing import List

from modules.models import Bookmaker, Country, Employee, Match, Source


@dataclass
class ReportParsed:
    msg_id: str
    date: str
    status: str

    source: Source  # partner
    country: Country  # country
    bookmaker: Bookmaker  # bookmaker
    match_: Match  # match
    
    count: int
    employees: List[Employee]
    nickname: str
    
    stake: float
    coefficient: float
    return_amount: float  # Возврат (если не указан - рассчитывается автоматически)

    is_error: bool
    is_over: bool
    is_express: bool
    delete: bool

