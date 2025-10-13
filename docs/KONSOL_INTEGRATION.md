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

### Автоматическое создание платежей из заявок

Платежи создаются автоматически при принятии заявки админом:


## Webhook события

Поддерживаемые типы событий:

- `payment.created` - Платеж создан
- `payment.updated` - Платеж обновлен
- `payment.completed` - Платеж завершен
- `payment.failed` - Платеж не удался
- `payment.cancelled` - Платеж отменен



## Логирование

Все операции с API konsol.pro логируются. Логи включают:

- Успешные запросы
- Ошибки соединения
- Ошибки API
- Webhook события

Логи доступны через `core.logger.api_logger`.
