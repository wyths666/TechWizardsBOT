from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminMenuCallback(CallbackData, prefix='admin_menu'):
    page: str


class ClaimCallback(CallbackData, prefix="claim"):
    claim_id: str
    action: str  # "accept", "reject", "message"


class AdminState(StatesGroup):
    waiting_message_to_user = State()
    waiting_reply_to_user = State()
    waiting_for_bank_id = State()

def claim_action_ikb_with_bank_button(claim_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для заявки СБП: кнопка заполнения ID банка + стандартные действия.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Заполнить ID банка", callback_data=f"fill_bank_id_{claim_id}")
    builder.button(text="💬 Написать пользователю", callback_data=f"message_{claim_id}")
    builder.button(text="👀 Просмотреть чат", callback_data=f"chat_{claim_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{claim_id}")
    builder.adjust(1)
    return builder.as_markup()


def claim_action_ikb(claim_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить оплату", callback_data=f"confirm_{claim_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{claim_id}")
    builder.button(text="💬 Написать пользователю", callback_data=f"message_{claim_id}")
    builder.button(text="👀 Просмотреть чат", callback_data=f"chat_{claim_id}")
    builder.adjust(1)
    return builder.as_markup()

def quick_messages_ikb(claim_id):
    """Быстрые шаблоны сообщений"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ввести свой текст", callback_data=f"custom_{claim_id}")
    builder.button(text="🔄 Уточнить скриншот", callback_data=f"ask_screenshot_{claim_id}")
    builder.button(text="💰 Уточнить платежные данные", callback_data=f"ask_payment_{claim_id}")
    builder.adjust(1)
    return builder.as_markup()

def admin_reply_ikb(claim_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Ответить", callback_data=f"message_{claim_id}")
    return builder.as_markup()

