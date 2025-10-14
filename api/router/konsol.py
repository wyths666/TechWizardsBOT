from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from api.schemas.response import ResponseBase
from api.schemas.konsol import (
    CreatePaymentRequest, PaymentResponse, FpsBankMemberResponse
)
from utils.api import auth_by_token
from utils.konsol_client import konsol_client
from core.logger import api_logger as logger
from db.beanie.models.models import KonsolPayment, User, Claim

router = APIRouter(
    tags=["Konsol Payments"],
    prefix='/konsol'
)


@router.post("/payments", response_model=ResponseBase)
async def create_payment(
    data: CreatePaymentRequest,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Создать новый платёж через Konsol API
    """
    try:
        # === Подготовка данных для API ===
        # Определяем тип выплаты
        bank_details_kind = "fps" if data.phone_number else "card"

        # Формируем реквизиты
        if bank_details_kind == "fps":
            if not data.fps_bank_member_id:
                raise HTTPException(status_code=400, detail="fps_bank_member_id обязателен для СБП")
            bank_details = {
                "fps_mobile_phone": data.phone_number,
                "fps_bank_member_id": data.fps_bank_member_id
            }
        else:
            bank_details = {
                "card_number": data.card_number
            }

        payment_payload = {
            "contractor_id": data.contractor_id,
            "services_list": [
                {
                    "title": data.purpose or "Выплата выигрыша",
                    "amount": str(data.amount)
                }
            ],
            "bank_details_kind": bank_details_kind,
            "bank_details": bank_details,
            "purpose": data.purpose or "Выплата выигрыша",
            "amount": str(data.amount)
        }

        # === Вызов Konsol API ===
        result = await konsol_client.create_payment(payment_payload)

        # === Сохранение в БД ===
        konsol_payment = await KonsolPayment.create(
            konsol_id=result.get("id"),
            contractor_id=data.contractor_id,
            amount=data.amount,
            status=result.get("status"),
            purpose=data.purpose or "Выплата выигрыша",
            services_list=payment_payload["services_list"],
            bank_details_kind=bank_details_kind,
            card_number=data.card_number,
            phone_number=data.phone_number,
            bank_member_id=data.fps_bank_member_id,
            claim_id=data.claim_id,
            user_id=data.user_id
        )

        logger.info(f"Payment created successfully: {result.get('id')}")
        return ResponseBase(
            success=True,
            data=result,
            message="Платёж успешно создан"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments/{konsol_id}", response_model=ResponseBase)
async def get_payment_status(
    konsol_id: str,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Получить статус платежа
    """
    try:
        # Сначала ищем в нашей БД
        db_payment = await KonsolPayment.get(konsol_id=konsol_id)

        if not db_payment:
            raise HTTPException(status_code=404, detail="Платёж не найден в локальной БД")

        # Запрашиваем статус из API
        try:
            api_result = await konsol_client.get_payment(konsol_id)

            # Обновляем статус в БД, если изменился
            if db_payment.status != api_result.get("status"):
                update_data = {"status": api_result.get("status"), "updated_at": datetime.now()}
                if api_result.get("status") == "executed" and not db_payment.paid_at:
                    update_data["paid_at"] = datetime.now()
                await db_payment.update(**update_data)

            result = api_result

        except Exception as api_error:
            logger.warning(f"Failed to fetch payment status from API: {api_error}")
            # Возвращаем данные из БД
            result = {
                "id": db_payment.konsol_id,
                "status": db_payment.status,
                "amount": str(db_payment.amount),
                "purpose": db_payment.purpose,
                "contractor_id": db_payment.contractor_id,
                "bank_details_kind": db_payment.bank_details_kind,
                "bank_details": {
                    "card_number": db_payment.card_number,
                    "fps_mobile_phone": db_payment.phone_number,
                    "fps_bank_member_id": db_payment.bank_member_id
                },
                "created_at": db_payment.created_at.isoformat(),
                "updated_at": db_payment.updated_at.isoformat(),
                "paid_at": db_payment.paid_at.isoformat() if db_payment.paid_at else None
            }

        return ResponseBase(
            success=True,
            data=result,
            message="Статус платежа получен"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payment status {konsol_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статуса платежа")


@router.get("/fps-bank-members", response_model=ResponseBase)
async def get_fps_bank_members(
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Получить список банков для СБП
    """
    try:
        result = await konsol_client.get_fps_bank_members()

        # Возвращаем только нужные поля
        members = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "bic": item.get("bic")
            }
            for item in result
        ]

        return ResponseBase(
            success=True,
            data=members,
            message="Список банков СБП получен"
        )

    except Exception as e:
        logger.error(f"Failed to get FPS bank members: {e}")
        raise HTTPException(status_code=400, detail=str(e))