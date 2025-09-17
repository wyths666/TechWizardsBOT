from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuCallback(CallbackData, prefix='menu'):
    page: str


menu_text = """
Меню
"""


def menu_ikb() -> InlineKeyboardMarkup:
    """
        Menu ikb
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text='Кнопка',
            callback_data=MenuCallback(page='btn').pack()
        )
    )
    builder.adjust(1)
    return builder.as_markup()
