from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from bot.templates.admin import menu as tadmin
from bot.filters.admin import IsAdmin
from bot.templates.admin import menu as tmenu

router = Router()
router.message.filter(IsAdmin())


# Заглушка: хранилище статусов заявок (вместо БД)
CLAIM_STATUSES = {}  # claim_id -> "accepted" / "rejected"


@router.callback_query(tadmin.ClaimCallback.filter())
async def handle_claim_action(call: CallbackQuery, callback_data: tadmin.ClaimCallback):
    claim_id = callback_data.claim_id
    action = callback_data.action

    # Обновляем статус (заглушка вместо БД)
    status = "Принята" if action == "accept" else "Отклонена"
    CLAIM_STATUSES[claim_id] = status

    # Удаляем кнопки и обновляем текст
    new_text = f"{call.message.text}\n\nСтатус: {status}"
    await call.message.edit_text(text=new_text)

    # Заглушка оплаты (только при принятии)
    if action == "accept":
        await fake_payment_api(claim_id)

    await call.answer()


async def fake_payment_api(claim_id: str):
    """Заглушка вместо реального API Konsol.pro"""
    print(f"[PAYMENT] Имитация оплаты по заявке {claim_id}")
    # Здесь позже будет вызов integrations/konsol.py
