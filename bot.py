import asyncio
import contextlib

from aiogram import Dispatcher, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommandScopeDefault, BotCommandScopeChat

from bot.handlers import routers
from config import cnf
from core.bot import bot
from core.logger import bot_logger as logger
from db.psql.crud.crud import init_psql

dp = Dispatcher(
    bot=bot,
    storage=MemoryStorage()
)
dp.include_routers(*routers)


async def startup(bot: Bot) -> None:
    """
        Активируется при выключении
    :param bot: Bot
    :return:
    """
    # Init dbs
    # await init_psql()
    # Setting bot
    await bot.delete_webhook()
    await bot.set_my_commands(
        commands=cnf.bot.COMMANDS,
        scope=BotCommandScopeDefault()
    )
    for admin in cnf.bot.ADMINS:
        with contextlib.suppress(TelegramBadRequest):
            await bot.set_my_commands(
                cnf.bot.COMMANDS + cnf.bot.ADMIN_COMMANDS,
                scope=BotCommandScopeChat(chat_id=admin)
            )

    logger.info('=== Bot started ===')


async def shutdown(bot: Bot) -> None:
    """
        Активируется при выключении
    :param bot: Bot
    :return:
    """
    await bot.close()
    await dp.stop_polling()

    logger.info('=== Bot stopped ===')


async def main() -> None:
    """
        Start the bot
    :return:
    """
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Exit')
