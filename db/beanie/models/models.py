from typing import Optional, Union, Dict, Any
from beanie import Document
from datetime import datetime
import pytz

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Базовый класс для CRUD-операций
class ModelAdmin(Document):
    class CellTypeExp(Exception):
        pass

    @classmethod
    async def create(cls, data: dict = None, **kwargs): # type: ignore
        """
        Создает новый объект и вставляет его в базу данных.
        """
        if data: 
            kwargs = data
        obj = cls(**kwargs)

        await obj.insert()
        return obj

    async def update(self, **kwargs):
        """
        Обновляет поля объекта новыми значениями.
        """
        _set = {"$set": {}}

        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise self.CellTypeExp(f"В модели `{self.__class__.__name__}` отсутствует поле `{key}`")
            elif not isinstance(self.__dict__.get(key), type(value)):
                raise self.CellTypeExp(
                    f"Тип данных поля `{key}` модели `{self.__class__.__name__}` является {type(self.__dict__.get(key))} (не {type(value)})")
            _set["$set"][key] = value

        await super().update(_set)

    async def delete(self):
        """
        Удаляет объект из базы данных.
        """
        await super().delete()

    @classmethod
    async def get(cls, **kwargs):
        """
        Возвращает один объект, соответствующий критериям поиска.
        """
        return await cls.find_one(kwargs)

    @classmethod
    async def check(cls, **kwargs) -> Optional[str]:
        """
        Проверяет наличие объекта, соответствующего критериям поиска, и возвращает его ID.
        """
        obj = await cls.find_one(kwargs)
        return str(obj.id) if obj else None

    @classmethod
    async def filter(cls, **kwargs):
        """
        Возвращает список объектов, соответствующих критериям поиска.
        """
        return await cls.find(kwargs).to_list()

    @classmethod
    async def all(cls):
        """
        Возвращает список всех объектов.
        """
        return await cls.find_all().to_list()


class AdminMessage(ModelAdmin):
    claim_id: str
    from_admin_id: int
    to_user_id: int
    message_text: str = ""
    is_reply: bool = False
    created_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "admin_messages"


class User(ModelAdmin):
    tg_id: int
    username: Optional[str] = None
    role: str = "user"
    created_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "users"

class Claim(ModelAdmin):
    claim_id: str                   # "000001"
    user_id: int                    # tg_id
    code: str
    code_status: str                # "valid" / "invalid"
    process_status: str             # "process" / "complete" / "cancelled"
    claim_status: str               # "confirm" / "cancelled"
    payment_method: str             # "phone" / "card"
    amount: float = 1000.00         # Сумма платежа (по умолчанию 1000 руб)
    phone: Optional[str] = None
    card: Optional[str] = None
    bank: Optional[str] = None
    review_text: str = ""
    photo_file_ids: list[str] = []
    created_at: datetime = datetime.now(MOSCOW_TZ)
    updated_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "claims"

    @classmethod
    async def generate_next_claim_id(cls) -> str:
        """
        Генерирует следующий номер заявки в формате 000001, 000002, ...
        """
        last_claim = await cls.find_all().sort("-claim_id").limit(1).to_list()
        if last_claim:
            last_num = int(last_claim[0].claim_id)
            return f"{last_num + 1:06d}"
        return "000001"


class KonsolPayment(ModelAdmin):
    """Модель для платежей konsol.pro"""
    konsol_id: str  # ID платежа в konsol.pro
    amount: float
    currency: str  # RUB, USD, EUR, etc.
    status: str  # pending, processing, completed, failed, cancelled
    description: Optional[str] = None
    payment_type: str  # card_payment, phone_payment
    user_id: Optional[int] = None  # tg_id пользователя
    external_id: Optional[str] = None  # Внешний ID для связи с другими системами
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Дополнительные данные в JSON
    payment_url: Optional[str] = None  # URL для оплаты
    created_at: datetime = datetime.now(MOSCOW_TZ)
    updated_at: datetime = datetime.now(MOSCOW_TZ)
    paid_at: Optional[datetime] = None  # Дата оплаты
    
    # Поля для платежа по карте
    card_number: Optional[str] = None  # Номер карты
    
    # Поля для платежа по телефону
    phone_number: Optional[str] = None  # Номер телефона
    bank: Optional[str] = None  # Банк

    class Settings:
        name = "konsol_payments"
        indexes = [
            "konsol_id",
            "user_id",
            "status",
            "currency",
            "external_id",
            "payment_type",
            "card_number",
            "phone_number"
        ]


class KonsolInvoice(ModelAdmin):
    """Модель для счетов konsol.pro"""
    konsol_id: str  # ID счета в konsol.pro
    amount: float
    currency: str  # RUB, USD, EUR, etc.
    status: str  # pending, processing, completed, failed, cancelled
    description: Optional[str] = None
    due_date: Optional[datetime] = None  # Дата оплаты счета
    user_id: Optional[int] = None  # tg_id пользователя
    external_id: Optional[str] = None  # Внешний ID для связи с другими системами
    metadata: Optional[Dict[str, Any]] = None  # Дополнительные данные в JSON
    invoice_url: Optional[str] = None  # URL для оплаты счета
    created_at: datetime = datetime.now(MOSCOW_TZ)
    updated_at: datetime = datetime.now(MOSCOW_TZ)
    paid_at: Optional[datetime] = None  # Дата оплаты

    class Settings:
        name = "konsol_invoices"
        indexes = [
            "konsol_id",
            "user_id",
            "status",
            "currency",
            "external_id"
        ]


class KonsolWebhookLog(ModelAdmin):
    """Модель для логов webhook уведомлений konsol.pro"""
    event: str  # Тип события
    data: Dict[str, Any]  # Данные события
    signature: Optional[str] = None  # Подпись для проверки
    processed: bool = False  # Обработано ли событие
    error_message: Optional[str] = None  # Сообщение об ошибке при обработке
    created_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "konsol_webhook_logs"
        indexes = [
            "event",
            "processed",
            "created_at"
        ]

