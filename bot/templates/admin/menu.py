from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminMenuCallback(CallbackData, prefix='admin_menu'):
    page: str

class ClaimCallback(CallbackData, prefix="claim"):
    action: str  # "accept", "reject"
    claim_id: str  # номер заявки, например "000001"


def claim_action_ikb(claim_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Принять",
        callback_data=ClaimCallback(action="accept", claim_id=claim_id)
    )
    builder.button(
        text="❌ Отклонить",
        callback_data=ClaimCallback(action="reject", claim_id=claim_id)
    )
    builder.adjust(2)
    return builder.as_markup()
