# Интеграция с API konsol.pro

## Описание

Данный проект интегрирован с API konsol.pro для обработки платежей. Интеграция включает в себя:

- Клиент для работы с API konsol.pro
- Модели данных для хранения информации о платежах
- REST API эндпоинты для управления платежами
- Обработка webhook уведомлений

## Настройка

### 1. Конфигурация

Добавьте в ваш `.env` файл следующие переменные:

```env
# Konsol.pro Configuration
KONSOL_API_TOKEN=your_konsol_api_token_here
KONSOL_BASE_URL=https://swagger-payments.konsol.pro
KONSOL_TIMEOUT=30
```

### 2. Настройка базы данных

Интеграция использует MongoDB через Beanie ODM. Модели автоматически создаются при первом запуске приложения.

**Модели данных:**

- `KonsolPayment` - для хранения платежей konsol.pro
- `KonsolInvoice` - для хранения счетов konsol.pro  
- `KonsolWebhookLog` - для логов webhook уведомлений

**Индексы автоматически создаются для:**
- `konsol_id` - уникальный идентификатор
- `user_id` - ID пользователя Telegram
- `status` - статус платежа/счета
- `currency` - валюта
- `external_id` - внешний идентификатор

Никаких дополнительных действий по созданию коллекций не требуется - Beanie автоматически создаст их при первом обращении.

## API Эндпоинты

### Платежи

#### Создать платеж по номеру карты
```http
POST /konsol/payments
Authorization: Bearer {your_api_token}
Content-Type: application/json

{
    "amount": 1000.00,
    "currency": "RUB",
    "description": "Оплата услуг",
    "payment_type": "card_payment",
    "card_number": "1234567890123456",
    "user_id": 123456789,
    "external_id": "order_123",
    "callback_url": "https://your-domain.com/webhook",
    "metadata": {
        "order_id": "123",
        "product": "premium"
    }
}
```

#### Создать платеж по номеру телефона и банку
```http
POST /konsol/payments
Authorization: Bearer {your_api_token}
Content-Type: application/json

{
    "amount": 1000.00,
    "currency": "RUB",
    "description": "Оплата услуг",
    "payment_type": "phone_payment",
    "phone_number": "+79123456789",
    "bank": "Сбербанк",
    "user_id": 123456789,
    "external_id": "order_123",
    "callback_url": "https://your-domain.com/webhook",
    "metadata": {
        "order_id": "123",
        "product": "premium"
    }
}
```

#### Получить платеж
```http
GET /konsol/payments/{payment_id}
Authorization: Bearer {your_api_token}
```

#### Получить список платежей
```http
GET /konsol/payments?status=completed&currency=RUB&page=1&per_page=10
Authorization: Bearer {your_api_token}
```

#### Обновить платеж
```http
PUT /konsol/payments/{payment_id}
Authorization: Bearer {your_api_token}
Content-Type: application/json

{
    "status": "completed",
    "description": "Обновленное описание"
}
```

#### Отменить платеж
```http
DELETE /konsol/payments/{payment_id}
Authorization: Bearer {your_api_token}
```

### Баланс

#### Получить баланс
```http
GET /konsol/balance
Authorization: Bearer {your_api_token}
```

### Webhook

#### Обработка webhook уведомлений
```http
POST /konsol/webhook
Content-Type: application/json

{
    "event": "payment.completed",
    "data": {
        "id": "payment_123",
        "amount": 1000.00,
        "status": "completed"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "signature": "webhook_signature"
}
```

## Использование в коде

### Автоматическое создание платежей из заявок

Платежи создаются автоматически при принятии заявки админом:

```python
# При принятии заявки админом вызывается:
await create_konsol_payment(claim)

# Функция автоматически определяет тип платежа на основе claim.payment_method:
# - "card" → payment_type = "card_payment" 
# - "phone" → payment_type = "phone_payment"

# Создается платеж с данными из заявки:
payment_data = {
    "amount": claim.amount,  # Сумма из заявки
    "currency": "RUB",
    "description": f"Оплата по заявке {claim.claim_id}",
    "payment_type": payment_type,
    "user_id": claim.user_id,
    "external_id": f"claim_{claim.claim_id}"
}
```

### Ручное создание платежа

```python
from utils.konsol_client import konsol_client

# Создание платежа по номеру карты
card_payment_data = {
    "amount": 1000.00,
    "currency": "RUB",
    "description": "Оплата услуг",
    "payment_type": "card_payment",
    "card_number": "1234567890123456",
    "user_id": 123456789,
    "external_id": "order_123"
}

result = await konsol_client.create_payment(card_payment_data)
print(f"Платеж по карте создан: {result['id']}")

# Создание платежа по номеру телефона и банку
phone_payment_data = {
    "amount": 1000.00,
    "currency": "RUB",
    "description": "Оплата услуг",
    "payment_type": "phone_payment",
    "phone_number": "+79123456789",
    "bank": "Сбербанк",
    "user_id": 123456789,
    "external_id": "order_124"
}

result = await konsol_client.create_payment(phone_payment_data)
print(f"Платеж по телефону создан: {result['id']}")
```

### Получение информации о платеже

```python
payment_info = await konsol_client.get_payment("payment_123")
print(f"Статус платежа: {payment_info['status']}")
```

### Работа с базой данных

```python
from db.beanie.models.models import KonsolPayment
from datetime import datetime

# Создание записи в базе данных (платеж по карте)
card_payment = await KonsolPayment.create(
    konsol_id="payment_123",
    amount=1000.00,
    currency="RUB",
    status="pending",
    payment_type="card_payment",
    card_number="1234567890123456",
    user_id=123456789,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Создание записи в базе данных (платеж по телефону)
phone_payment = await KonsolPayment.create(
    konsol_id="payment_124",
    amount=1000.00,
    currency="RUB",
    status="pending",
    payment_type="phone_payment",
    phone_number="+79123456789",
    bank="Сбербанк",
    user_id=123456789,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Обновление статуса
await card_payment.update(status="completed", paid_at=datetime.now())

# Получение платежей пользователя
user_payments = await KonsolPayment.find(
    KonsolPayment.user_id == 123456789
).sort("-created_at").limit(10).to_list()

# Поиск по статусу
pending_payments = await KonsolPayment.find(
    KonsolPayment.status == "pending"
).to_list()

# Поиск по типу платежа
card_payments = await KonsolPayment.find(
    KonsolPayment.payment_type == "card_payment"
).to_list()

phone_payments = await KonsolPayment.find(
    KonsolPayment.payment_type == "phone_payment"
).to_list()
```

## Webhook события

Поддерживаемые типы событий:

- `payment.created` - Платеж создан
- `payment.updated` - Платеж обновлен
- `payment.completed` - Платеж завершен
- `payment.failed` - Платеж не удался
- `payment.cancelled` - Платеж отменен


## Обработка ошибок

Все методы клиента могут выбрасывать исключения:

- `aiohttp.ClientError` - Ошибки соединения
- `Exception` - Ошибки API (коды 4xx, 5xx)

Пример обработки ошибок:

```python
try:
    result = await konsol_client.create_payment(payment_data)
except Exception as e:
    print(f"Ошибка создания платежа: {e}")
```

## Логирование

Все операции с API konsol.pro логируются. Логи включают:

- Успешные запросы
- Ошибки соединения
- Ошибки API
- Webhook события

Логи доступны через `core.logger.api_logger`.

## Безопасность

- Все запросы к API требуют аутентификации по токену
- Webhook уведомления могут содержать подпись для проверки подлинности
- Чувствительные данные (API токены) хранятся в переменных окружения


## Дополнительные ресурсы

- [Документация konsol.pro API](https://swagger-payments.konsol.pro)
- [Поддержка konsol.pro](https://support.konsol.pro)
