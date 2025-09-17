from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.filters.user import NewUser
from bot.templates.user import menu as tmenu
from bot.templates.user import reg as treg

router = Router()


@router.message(Command("start"), NewUser())
async def new_user_start(msg: Message, state: FSMContext):
    """
        /start command of new user
    :param msg: Message
    :param state: FSMContext
    :return:
    """
    await msg.answer(
        text=treg.name_text
    )

    await state.set_state(treg.RegState.name)
    await msg.delete()


@router.message(Command("start"))
async def start_command(msg: Message, state: FSMContext):
    """
        /start command
    :param msg: Message
    :param state: FSMContext
    :return:
    """
    await msg.answer(
        text=tmenu.menu_text,
        reply_markup=tmenu.menu_ikb()
    )

    await msg.delete()
