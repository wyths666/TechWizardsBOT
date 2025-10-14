import pytz
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from beanie import Document


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

    # === Поля для Konsol API ===
    contractor_id: Optional[str] = None  # UUID от Konsol
    kind: str = "individual"  # всегда "individual"
    taxpayer_id: Optional[str] = None  # ИНН (не обязателен)

    # === Последние реквизиты для выплат (для удобства) ===
    # last_fps_mobile_phone: Optional[str] = None  # для СБП
    # last_fps_bank_member_id: Optional[str] = None  # ID банка из справочника СБП
    # last_card_number: Optional[str] = None  # для выплат на карту

    created_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "users"


class Claim(ModelAdmin):
    claim_id: str  # "000001"
    user_id: int  # tg_id
    code: str
    code_status: str  # "valid" / "invalid"
    process_status: str = "process"  # "process" / "complete" / "cancelled"
    claim_status: str = "pending"  # "pending", "confirm", "cancelled"
    payment_method: str  # "phone" / "card"
    amount: Decimal = Decimal("1.00")  # Сумма платежа (хранится как Decimal)

    # === Реквизиты из заявки (не дублируются в User) ===
    phone: Optional[str] = None  # если выбрана СБП
    card: Optional[str] = None  # если выбрана карта
    bank_member_id: Optional[str] = None  # если выбрана СБП

    review_text: str = ""
    photo_file_ids: List[str] = []

    # === Связь с платежом ===
    konsol_payment_id: Optional[str] = None  # ID в коллекции konsol_payments

    created_at: datetime = datetime.now(MOSCOW_TZ)
    updated_at: datetime = datetime.now(MOSCOW_TZ)

    class Settings:
        name = "claims"
        use_state_management = True

    def update_status(self, claim_status: str, process_status: str):
        """Метод для обновления статусов"""
        self.claim_status = claim_status
        self.process_status = process_status
        self.updated_at = datetime.now(MOSCOW_TZ)

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
    konsol_id: Optional[str] = None  # ID платежа в konsol.pro (заполняется после создания)
    contractor_id: str  # ID исполнителя в Konsol (берётся из User)
    amount: Decimal = Decimal("1.00")  # Сумма (Decimal)
    status: str  # created, manualpay, executed, failed, nalog_unbound
    purpose: str  # Назначение платежа
    services_list: List[Dict[str, Any]]  # Список услуг: [{"title": "...", "amount": "100.00"}]
    bank_details_kind: str  # "fps", "card", "bank_account"

    # === Реквизиты (только одно заполнено в зависимости от bank_details_kind) ===
    card_number: Optional[str] = None  # Для kind="card"
    phone_number: Optional[str] = None  # Для kind="fps"
    bank_member_id: Optional[str] = None  # Для kind="fps" — ID банка из справочника

    # === Связь с заявкой и пользователем ===
    claim_id: Optional[str] = None  # ID заявки (из Claim)
    user_id: Optional[int] = None  # tg_id пользователя (для удобства поиска)

    # === Временные метки ===
    created_at: datetime = datetime.now(MOSCOW_TZ)
    updated_at: datetime = datetime.now(MOSCOW_TZ)
    paid_at: Optional[datetime] = None  # Заполняется при статусе "executed"

    class Settings:
        name = "konsol_payments"
        indexes = [
            "konsol_id",
            "user_id",
            "status",
            "contractor_id",
            "claim_id",
            "bank_details_kind",
            "phone_number",
            "card_number"
        ]






