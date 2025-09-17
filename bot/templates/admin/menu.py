from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminMenuCallback(CallbackData, prefix='admin_menu'):
    page: str


menu_text = """
Привет, Админ!
"""


def menu_ikb() -> InlineKeyboardMarkup:
    """
        Admin menu ikb
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text='✉️ Рассылка',
            callback_data=AdminMenuCallback(page='mailing').pack()
        ),
    )
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()
