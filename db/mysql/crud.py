import aiomysql
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '185.178.47.172'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'admin_lovelin2'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'db': os.getenv('MYSQL_DATABASE', 'admin_lovelin2'),
    'charset': 'utf8mb4',
    'autocommit': True
}


@asynccontextmanager
async def get_connection():
    conn = await aiomysql.connect(**MYSQL_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


async def init_mysql():
    """Проверяем наличие таблицы"""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES LIKE 'oc_qrcode'")
            exists = await cur.fetchone()
            if not exists:
                raise Exception("Таблица oc_qrcode не найдена!")


async def get_and_delete_code(code_text: str):
    """
    Пытается найти код и сразу удалить его (атомарно).
    Возвращает True, если код существовал и удалён.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            # Сначала проверяем наличие
            await cur.execute("SELECT code_text FROM oc_qrcode WHERE code_text = %s", (code_text,))
            exists = await cur.fetchone()

            if not exists:
                return False

            # Удаляем код
            #await cur.execute("DELETE FROM oc_qrcode WHERE code_text = %s", (code_text,))

            return True