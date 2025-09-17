from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State


class RegState(StatesGroup):
    name = State()


class RegCallback(CallbackData, prefix='reg'):
    step: str


name_text = """
Пришлите ваше имя:
"""
