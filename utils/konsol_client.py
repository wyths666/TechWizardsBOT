import aiohttp
from typing import Dict, Any, Optional, List
from decimal import Decimal

from core.logger import api_logger as logger
from config import cnf


class KonsolAPIClient:
    """Клиент для работы с API konsol.pro"""

    def __init__(self):
        self.base_url = cnf.konsol.BASE_URL.rstrip("/")  # убираем лишний слэш
        self.token = cnf.konsol.TOKEN  # используем TOKEN из config
        self.timeout = aiohttp.ClientTimeout(total=cnf.konsol.TIMEOUT or 30)

    async def _make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API konsol.pro

        :param method: HTTP метод (GET, POST, ...)
        :param endpoint: Эндпоинт (например: /api/v1/payments)
        :param data: Тело запроса
        :param params: GET-параметры
        :return: Ответ API
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
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
                        raise Exception(f"API Error {response.status}: {response_data}")

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
        Создает новый платёж

        :param payment_data: {
            "contractor_id": "uuid",
            "services_list": [{"title": "Выплата", "amount": "100.00"}],
            "bank_details_kind": "fps" | "card" | "bank_account",
            "bank_details": {...},
            "purpose": "Назначение",
            "amount": "100.00"
        }
        :return: Ответ API
        """
        return await self._make_request("POST", "/api/v1/payments", data=payment_data)

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Получает информацию о платеже

        :param payment_id: ID платежа
        :return: Информация о платеже
        """
        return await self._make_request("GET", f"/api/v1/payments/{payment_id}")

    async def get_fps_bank_members(self) -> List[Dict[str, Any]]:
        """
        Получает список банков для СБП

        :return: [
          {
            "id": "100000000011",
            "name": "Сбербанк",
            "bic": "046577964"
          },
          ...
        ]
        """
        return await self._make_request("GET", "/api/v1/references/fps_bank_members")

    async def get_company_accounts(self) -> Dict[str, Any]:
        return await self._make_request("GET", "/api/v1/company_accounts")

    # === НОВЫЙ МЕТОД ===
    async def create_contractor(self, contractor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает нового контрактора в Konsol API

        :param contractor_data: {
            "kind": "individual" | "self_employed",
            "taxpayer_id": "..." (опционально для individual)
        }
        :return: Ответ API (обычно с id контрактора)
        """
        return await self._make_request("POST", "/api/v1/contractors", data=contractor_data)


# Глобальный экземпляр клиента
konsol_client = KonsolAPIClient()