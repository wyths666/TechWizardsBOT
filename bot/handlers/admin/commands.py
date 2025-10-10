# bot/handlers/admin/menu.py

from aiogram import Router, types
from aiogram.types import CallbackQuery
from bot.templates.admin import menu as tadmin
from db.beanie.models import Claim  # ← подключаем модель
from core.bot import bot

router = Router()

@router.callback_query(tadmin.ClaimCallback.filter())
async def handle_claim_action(call: CallbackQuery, callback_data: tadmin.ClaimCallback):
    claim_id = callback_data.claim_id
    action = callback_data.action

    # === Находим заявку в MongoDB ===
    claim = await Claim.get(claim_id=claim_id)
    if not claim:
        await call.answer("Заявка не найдена в базе.", show_alert=True)
        return

    # === Определяем статусы ===
    if action == "accept":
        claim_status = "confirm"
        process_status = "complete"
        status_text = "Принята"
        # Имитация оплаты
        await fake_payment_api(claim_id)
    else:  # "reject"
        claim_status = "cancelled"
        process_status = "cancelled"
        status_text = "Отклонена"

    # === Обновляем заявку в MongoDB ===
    await claim.update(
        claim_status=claim_status,
        process_status=process_status
    )

    # === Обновляем сообщение в группе ===
    new_text = f"{call.message.text}\n\nСтатус: {status_text}"
    await call.message.edit_text(text=new_text)

    await call.answer()


async def fake_payment_api(claim_id: str):
    """Заглушка вместо реального API Konsol.pro"""
    print(f"[PAYMENT] Имитация оплаты по заявке {claim_id}")
    # TODO: в будущем — вызов integrations/konsol.py