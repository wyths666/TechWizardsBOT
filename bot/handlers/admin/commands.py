from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.filters.admin import IsAdmin
from bot.templates.admin import menu as tmenu

router = Router()
router.message.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_menu(msg: Message, state: FSMContext):
    """
        /admin command
    :param msg: Message
    :param state: FSMContext
    :return:
    """
    await msg.answer(
        text=tmenu.menu_text,
        reply_markup=tmenu.menu_ikb()
    )

    await msg.delete()
