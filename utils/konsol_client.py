import aiohttp
from typing import Dict, Any, Optional
from core.logger import api_logger as logger
from config import cnf


class KonsolAPIClient:
    """Клиент для работы с API konsol.pro"""
    
    def __init__(self):
        self.base_url = cnf.konsol.BASE_URL
        self.token = cnf.konsol.API_TOKEN
        self.timeout = cnf.konsol.TIMEOUT
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API konsol.pro
        
        :param method: HTTP метод (GET, POST, PUT, DELETE)
        :param endpoint: Эндпоинт API
        :param data: Данные для отправки в теле запроса
        :param params: Параметры запроса
        :return: Ответ от API
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                ) as response:
                    response_data = await response.json()
                    
                    if response.status >= 400:
                        logger.error(f"Konsol API error: {response.status} - {response_data}")
                        raise Exception(f"API Error: {response.status} - {response_data}")
                    
                    logger.info(f"Konsol API request successful: {method} {endpoint}")
                    return response_data
                    
        except aiohttp.ClientError as e:
            logger.error(f"Konsol API connection error: {e}")
            raise Exception(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Konsol API request error: {e}")
            raise

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новый платеж
        
        :param payment_data: Данные платежа
        :return: Информация о созданном платеже
        """
        # Подготавливаем данные для konsol.pro API
        api_data = {
            "amount": payment_data.get("amount"),
            "currency": payment_data.get("currency"),
            "description": payment_data.get("description"),
            "user_id": payment_data.get("user_id"),
            "external_id": payment_data.get("external_id"),
            "callback_url": payment_data.get("callback_url"),
            "metadata": payment_data.get("metadata", {})
        }
        
        # Добавляем поля в зависимости от типа платежа
        payment_type = payment_data.get("payment_type")
        if payment_type == "card_payment":
            api_data["payment_method"] = "card"
            api_data["card_number"] = payment_data.get("card_number")
        elif payment_type == "phone_payment":
            api_data["payment_method"] = "phone"
            api_data["phone_number"] = payment_data.get("phone_number")
            api_data["bank"] = payment_data.get("bank")
        
        # Добавляем тип платежа в метаданные
        api_data["metadata"]["payment_type"] = payment_type
        
        return await self._make_request("POST", "/api/payments", data=api_data)
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Получает информацию о платеже
        
        :param payment_id: ID платежа
        :return: Информация о платеже
        """
        return await self._make_request("GET", f"/api/payments/{payment_id}")
    
    async def get_payments(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Получает список платежей
        
        :param params: Параметры фильтрации
        :return: Список платежей
        """
        return await self._make_request("GET", "/api/payments", params=params)
    
    async def update_payment(self, payment_id: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновляет платеж
        
        :param payment_id: ID платежа
        :param payment_data: Новые данные платежа
        :return: Обновленная информация о платеже
        """
        return await self._make_request("PUT", f"/api/payments/{payment_id}", data=payment_data)
    
    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Отменяет платеж
        
        :param payment_id: ID платежа
        :return: Результат отмены
        """
        return await self._make_request("DELETE", f"/api/payments/{payment_id}")
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Получает текущий баланс
        
        :return: Информация о балансе
        """
        return await self._make_request("GET", "/api/balance")



# Глобальный экземпляр клиента
konsol_client = KonsolAPIClient()
