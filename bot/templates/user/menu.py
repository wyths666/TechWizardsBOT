from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.templates.user.reg import RegCallback


class MenuCallback(CallbackData, prefix='menu'):
    page: str





def support_ikb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Тех. поддержка", url="https://t.me/EkaterinaKazantseva31"))
    return builder.as_markup()


def send_screenshot_ikb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Прислать скриншот", callback_data=RegCallback(step="send_screenshot"))
    return builder.as_markup()


def phone_or_card_ikb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Указать номер телефона", callback_data=RegCallback(step="phone"))
    builder.button(text="Указать номер карты", callback_data=RegCallback(step="card"))
    builder.adjust(1)
    return builder.as_markup()


def check_subscription_ikb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Проверить подписку", callback_data=RegCallback(step="check_sub"))
    return builder.as_markup()