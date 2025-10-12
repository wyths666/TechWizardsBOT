from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from datetime import datetime

from api.schemas.response import ResponseBase
from api.schemas.konsol import (
    CreatePaymentRequest, UpdatePaymentRequest, PaymentResponse, PaymentsListResponse,
    BalanceResponse, PaymentFilters, WebhookPayload
)
from utils.api import auth_by_token
from utils.konsol_client import konsol_client
from core.logger import api_logger as logger
from db.beanie.models.models import KonsolPayment, KonsolInvoice, KonsolWebhookLog

router = APIRouter(
    tags=["Konsol Payments"],
    prefix='/konsol'
)


# Эндпоинты для работы с платежами
@router.post("/payments", response_model=ResponseBase)
async def create_payment(
    data: CreatePaymentRequest,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Создать новый платеж
    
    :param data: Данные для создания платежа
    :param auth: Аутентификация по токену
    :return: Результат создания платежа
    """
    try:
        payment_data = data.model_dump(exclude_none=True)
        result = await konsol_client.create_payment(payment_data)
        
        # Сохраняем платеж в базу данных
        db_payment_data = {
            "konsol_id": result.get('id'),
            "amount": result.get('amount'),
            "currency": result.get('currency'),
            "status": result.get('status'),
            "description": result.get('description'),
            "payment_type": data.payment_type,
            "user_id": result.get('user_id'),
            "external_id": result.get('external_id'),
            "callback_url": result.get('callback_url'),
            "metadata": result.get('metadata'),
            "payment_url": result.get('payment_url'),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Добавляем специфичные поля в зависимости от типа платежа
        if data.payment_type == "card_payment":
            db_payment_data["card_number"] = data.card_number
        elif data.payment_type == "phone_payment":
            db_payment_data["phone_number"] = data.phone_number
            db_payment_data["bank"] = data.bank
        
        db_payment = await KonsolPayment.create(**db_payment_data)
        
        logger.info(f"Payment created successfully: {result.get('id')}")
        return ResponseBase(
            success=True,
            data=result,
            message="Платеж успешно создан"
        )
        
    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments/{payment_id}", response_model=ResponseBase)
async def get_payment(
    payment_id: str,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Получить информацию о платеже
    
    :param payment_id: ID платежа
    :param auth: Аутентификация по токену
    :return: Информация о платеже
    """
    try:
        # Сначала пытаемся получить из нашей базы данных
        db_payment = await KonsolPayment.get(konsol_id=payment_id)
        
        if db_payment:
            # Обновляем данные из konsol.pro API
            try:
                api_result = await konsol_client.get_payment(payment_id)
                
                # Обновляем статус в базе данных если изменился
                if db_payment.status != api_result.get('status'):
                    await db_payment.update(
                        status=api_result.get('status'),
                        updated_at=datetime.now(),
                        paid_at=datetime.now() if api_result.get('status') == 'completed' else db_payment.paid_at
                    )
                
                result = api_result
            except Exception:
                # Если API недоступен, возвращаем данные из базы
                result = {
                    'id': db_payment.konsol_id,
                    'amount': db_payment.amount,
                    'currency': db_payment.currency,
                    'status': db_payment.status,
                    'description': db_payment.description,
                    'payment_type': db_payment.payment_type,
                    'user_id': db_payment.user_id,
                    'external_id': db_payment.external_id,
                    'metadata': db_payment.metadata,
                    'payment_url': db_payment.payment_url,
                    'created_at': db_payment.created_at.isoformat(),
                    'updated_at': db_payment.updated_at.isoformat(),
                    'paid_at': db_payment.paid_at.isoformat() if db_payment.paid_at else None,
                    'card_number': db_payment.card_number,
                    'phone_number': db_payment.phone_number,
                    'bank': db_payment.bank
                }
        else:
            # Если нет в нашей базе, получаем из API и сохраняем
            result = await konsol_client.get_payment(payment_id)
            
            # Извлекаем тип платежа из метаданных
            metadata = result.get('metadata', {})
            payment_type = metadata.get('payment_type', 'card_payment')
            
            db_payment_data = {
                "konsol_id": result.get('id'),
                "amount": result.get('amount'),
                "currency": result.get('currency'),
                "status": result.get('status'),
                "description": result.get('description'),
                "payment_type": payment_type,
                "user_id": result.get('user_id'),
                "external_id": result.get('external_id'),
                "callback_url": result.get('callback_url'),
                "metadata": metadata,
                "payment_url": result.get('payment_url'),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "paid_at": datetime.now() if result.get('paid_at') else None
            }
            
            # Добавляем специфичные поля если есть в ответе API
            if result.get('card_number'):
                db_payment_data["card_number"] = result.get('card_number')
            if result.get('phone_number'):
                db_payment_data["phone_number"] = result.get('phone_number')
            if result.get('bank'):
                db_payment_data["bank"] = result.get('bank')
            
            await KonsolPayment.create(**db_payment_data)
        
        return ResponseBase(
            success=True,
            data=result,
            message="Информация о платеже получена"
        )
        
    except Exception as e:
        logger.error(f"Failed to get payment {payment_id}: {e}")
        raise HTTPException(status_code=404, detail="Платеж не найден")


@router.get("/payments", response_model=ResponseBase)
async def get_payments(
    status: Optional[str] = Query(None, description="Статус платежа"),
    currency: Optional[str] = Query(None, description="Валюта"),
    payment_method: Optional[str] = Query(None, description="Метод оплаты"),
    user_id: Optional[int] = Query(None, description="ID пользователя"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Получить список платежей с фильтрацией
    
    :param status: Фильтр по статусу
    :param currency: Фильтр по валюте
    :param payment_method: Фильтр по методу оплаты
    :param user_id: Фильтр по ID пользователя
    :param page: Номер страницы
    :param per_page: Количество элементов на странице
    :param auth: Аутентификация по токену
    :return: Список платежей
    """
    try:
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if status:
            params["status"] = status
        if currency:
            params["currency"] = currency
        if payment_method:
            params["payment_method"] = payment_method
        if user_id:
            params["user_id"] = user_id
            
        result = await konsol_client.get_payments(params)
        
        return ResponseBase(
            success=True,
            data=result,
            message="Список платежей получен"
        )
        
    except Exception as e:
        logger.error(f"Failed to get payments: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/payments/{payment_id}", response_model=ResponseBase)
async def update_payment(
    payment_id: str,
    data: UpdatePaymentRequest,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Обновить платеж
    
    :param payment_id: ID платежа
    :param data: Новые данные платежа
    :param auth: Аутентификация по токену
    :return: Результат обновления платежа
    """
    try:
        payment_data = data.model_dump(exclude_none=True)
        result = await konsol_client.update_payment(payment_id, payment_data)
        
        logger.info(f"Payment {payment_id} updated successfully")
        return ResponseBase(
            success=True,
            data=result,
            message="Платеж успешно обновлен"
        )
        
    except Exception as e:
        logger.error(f"Failed to update payment {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/payments/{payment_id}", response_model=ResponseBase)
async def cancel_payment(
    payment_id: str,
    auth: bool = Depends(auth_by_token)
) -> ResponseBase:
    """
    Отменить платеж
    
    :param payment_id: ID платежа
    :param auth: Аутентификация по токену
    :return: Результат отмены платежа
    """
    try:
        result = await konsol_client.cancel_payment(payment_id)
        
        logger.info(f"Payment {payment_id} cancelled successfully")
        return ResponseBase(
            success=True,
            data=result,
            message="Платеж успешно отменен"
        )
        
    except Exception as e:
        logger.error(f"Failed to cancel payment {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Эндпоинт для получения баланса
@router.get("/balance", response_model=ResponseBase)
async def get_balance(auth: bool = Depends(auth_by_token)) -> ResponseBase:
    """
    Получить текущий баланс
    
    :param auth: Аутентификация по токену
    :return: Информация о балансе
    """
    try:
        result = await konsol_client.get_balance()
        
        return ResponseBase(
            success=True,
            data=result,
            message="Баланс получен"
        )
        
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Эндпоинт для webhook уведомлений
@router.post("/webhook", response_model=ResponseBase)
async def webhook_handler(data: WebhookPayload) -> ResponseBase:
    """
    Обработчик webhook уведомлений от konsol.pro
    
    :param data: Данные webhook уведомления
    :return: Подтверждение получения
    """
    try:
        logger.info(f"Webhook received: {data.event} - {data.data}")
        
        # Сохраняем webhook в лог
        webhook_log = await KonsolWebhookLog.create(
            event=data.event,
            data=data.data,
            signature=data.signature,
            processed=False,
            created_at=datetime.now()
        )
        
        # Обрабатываем различные типы событий
        if data.event.startswith("payment."):
            await process_payment_webhook(data)

        # Отмечаем webhook как обработанный
        await webhook_log.update(processed=True)
        
        return ResponseBase(
            success=True,
            message="Webhook обработан успешно"
        )
        
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        
        # Сохраняем ошибку в лог если webhook_log существует
        if 'webhook_log' in locals():
            await webhook_log.update(
                processed=True,
                error_message=str(e)
            )
        
        raise HTTPException(status_code=400, detail=str(e))


async def process_payment_webhook(data: WebhookPayload):
    """Обработка webhook событий платежей"""
    payment_data = data.data
    payment_id = payment_data.get('id')
    
    if not payment_id:
        return
    
    # Обновляем или создаем запись в базе данных
    db_payment = await KonsolPayment.get(konsol_id=payment_id)
    
    if db_payment:
        # Обновляем существующий платеж
        update_data = {
            'status': payment_data.get('status', db_payment.status),
            'updated_at': datetime.now()
        }
        
        if payment_data.get('status') == 'completed' and not db_payment.paid_at:
            update_data['paid_at'] = datetime.now()
        
        await db_payment.update(**update_data)
    else:
        # Извлекаем тип платежа из метаданных
        metadata = payment_data.get('metadata', {})
        payment_type = metadata.get('payment_type', 'card_payment')
        
        db_payment_data = {
            "konsol_id": payment_id,
            "amount": payment_data.get('amount', 0),
            "currency": payment_data.get('currency', 'RUB'),
            "status": payment_data.get('status', 'pending'),
            "description": payment_data.get('description'),
            "payment_type": payment_type,
            "user_id": payment_data.get('user_id'),
            "external_id": payment_data.get('external_id'),
            "metadata": metadata,
            "payment_url": payment_data.get('payment_url'),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "paid_at": datetime.now() if payment_data.get('status') == 'completed' else None
        }
        
        # Добавляем специфичные поля если есть
        if payment_data.get('card_number'):
            db_payment_data["card_number"] = payment_data.get('card_number')
        if payment_data.get('phone_number'):
            db_payment_data["phone_number"] = payment_data.get('phone_number')
        if payment_data.get('bank'):
            db_payment_data["bank"] = payment_data.get('bank')
        
        await KonsolPayment.create(**db_payment_data)

