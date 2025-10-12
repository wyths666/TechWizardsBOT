from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    """Статусы платежей"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Методы оплаты"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    ELECTRONIC_WALLET = "electronic_wallet"
    CRYPTOCURRENCY = "cryptocurrency"


class PaymentType(str, Enum):
    """Типы платежей"""
    CARD_PAYMENT = "card_payment"  # Платеж по номеру карты
    PHONE_PAYMENT = "phone_payment"  # Платеж по номеру телефона и банку


class Currency(str, Enum):
    """Поддерживаемые валюты"""
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    BTC = "BTC"
    ETH = "ETH"


# Схемы для создания платежей
class CreatePaymentRequest(BaseModel):
    """Схема запроса для создания платежа"""
    amount: float = Field(..., description="Сумма платежа")
    currency: Currency = Field(..., description="Валюта платежа")
    description: str = Field(..., description="Описание платежа")
    payment_type: PaymentType = Field(..., description="Тип платежа")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    external_id: Optional[str] = Field(None, description="Внешний ID платежа")
    callback_url: Optional[str] = Field(None, description="URL для callback уведомлений")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    
    # Поля для платежа по карте
    card_number: Optional[str] = Field(None, description="Номер карты (для card_payment)")
    
    # Поля для платежа по телефону
    phone_number: Optional[str] = Field(None, description="Номер телефона (для phone_payment)")
    bank: Optional[str] = Field(None, description="Банк (для phone_payment)")
    
    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, v, values):
        payment_type = values.data.get('payment_type')
        if payment_type == PaymentType.CARD_PAYMENT and not v:
            raise ValueError('card_number обязателен для card_payment')
        if payment_type == PaymentType.PHONE_PAYMENT and v:
            raise ValueError('card_number не должен указываться для phone_payment')
        return v
    
    @field_validator('phone_number', 'bank')
    @classmethod
    def validate_phone_fields(cls, v, values):
        payment_type = values.data.get('payment_type')
        field_name = values.field_name
        
        if payment_type == PaymentType.PHONE_PAYMENT and not v:
            raise ValueError(f'{field_name} обязателен для phone_payment')
        if payment_type == PaymentType.CARD_PAYMENT and v:
            raise ValueError(f'{field_name} не должен указываться для card_payment')
        return v


class UpdatePaymentRequest(BaseModel):
    """Схема запроса для обновления платежа"""
    status: Optional[PaymentStatus] = Field(None, description="Новый статус платежа")
    description: Optional[str] = Field(None, description="Обновленное описание")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Обновленные дополнительные данные")


# Схемы ответов
class PaymentResponse(BaseModel):
    """Схема ответа с информацией о платеже"""
    id: str = Field(..., description="ID платежа")
    amount: float = Field(..., description="Сумма платежа")
    currency: Currency = Field(..., description="Валюта платежа")
    status: PaymentStatus = Field(..., description="Статус платежа")
    description: str = Field(..., description="Описание платежа")
    payment_type: PaymentType = Field(..., description="Тип платежа")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    external_id: Optional[str] = Field(None, description="Внешний ID платежа")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    paid_at: Optional[datetime] = Field(None, description="Дата оплаты")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    payment_url: Optional[str] = Field(None, description="URL для оплаты")
    
    # Поля для платежа по карте
    card_number: Optional[str] = Field(None, description="Номер карты")
    
    # Поля для платежа по телефону
    phone_number: Optional[str] = Field(None, description="Номер телефона")
    bank: Optional[str] = Field(None, description="Банк")


class BalanceResponse(BaseModel):
    """Схема ответа с информацией о балансе"""
    currency: Currency = Field(..., description="Валюта баланса")
    amount: float = Field(..., description="Текущий баланс")
    available: float = Field(..., description="Доступный баланс")
    frozen: float = Field(..., description="Заблокированный баланс")
    updated_at: datetime = Field(..., description="Дата последнего обновления")


class PaymentsListResponse(BaseModel):
    """Схема ответа со списком платежей"""
    payments: List[PaymentResponse] = Field(..., description="Список платежей")
    total: int = Field(..., description="Общее количество платежей")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Количество элементов на странице")
    pages: int = Field(..., description="Общее количество страниц")


# Схемы для фильтрации
class PaymentFilters(BaseModel):
    """Параметры фильтрации платежей"""
    status: Optional[PaymentStatus] = Field(None, description="Фильтр по статусу")
    currency: Optional[Currency] = Field(None, description="Фильтр по валюте")
    payment_method: Optional[PaymentMethod] = Field(None, description="Фильтр по методу оплаты")
    user_id: Optional[int] = Field(None, description="Фильтр по ID пользователя")
    date_from: Optional[datetime] = Field(None, description="Дата начала периода")
    date_to: Optional[datetime] = Field(None, description="Дата окончания периода")
    page: int = Field(1, ge=1, description="Номер страницы")
    per_page: int = Field(10, ge=1, le=100, description="Количество элементов на странице")





# Схемы для webhook уведомлений
class WebhookEvent(str, Enum):
    """Типы webhook событий"""
    PAYMENT_CREATED = "payment.created"
    PAYMENT_UPDATED = "payment.updated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_CANCELLED = "payment.cancelled"



class WebhookPayload(BaseModel):
    """Схема payload для webhook уведомлений"""
    event: WebhookEvent = Field(..., description="Тип события")
    data: Dict[str, Any] = Field(..., description="Данные события")
    timestamp: datetime = Field(..., description="Время события")
    signature: Optional[str] = Field(None, description="Подпись для проверки подлинности")
