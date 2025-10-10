from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import re
from bot.templates.admin import menu as tadmin
from bot.templates.user import reg as treg
from bot.templates.user import menu as tmenu
from bot.filters.user import NewUser
from core.bot import bot, bot_config
from db.beanie.models import User, Claim
from db.mysql.crud import get_and_delete_code
from utils.check_subscribe import check_user_subscription
from asyncio import Lock

router = Router()
user_locks = {}


@router.message(Command("start"), NewUser())
async def start_new_user(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    username = msg.from_user.username

    # Определяем роль на основе BOT_ADMINS из .env
    role = "admin" if user_id in bot_config.ADMINS else "user"

    # Создаём пользователя в MongoDB
    await User.create(
        tg_id=user_id,
        username=username,
        role=role
    )

    await msg.answer(text=treg.start_text)
    await state.set_state(treg.RegState.waiting_for_code)
    await msg.delete()


@router.message(StateFilter(treg.RegState.waiting_for_code))
async def process_code(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()

    code_valid = await get_and_delete_code(code)
    if not code_valid:
        await msg.answer(text=treg.code_not_found_text, reply_markup=tmenu.support_ikb())
        return

    CHANNEL_USERNAME = "@zdorovkakslon"
    is_subscribed = await check_user_subscription(bot, msg.from_user.id, CHANNEL_USERNAME)

    if not is_subscribed:
        await msg.answer(
            text=treg.not_subscribed_text,
            reply_markup=tmenu.check_subscription_ikb()
        )
        # Сохраняем код для последующей проверки
        await state.update_data(entered_code=code)
        return

    # Успешно — идём к отзыву
    await proceed_to_review(msg, state, code)

@router.callback_query(treg.RegCallback.filter(F.step == "check_sub"))
async def check_subscription_callback(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("entered_code")

    if not code:
        await call.answer("Сессия устарела. Пожалуйста, введите код снова.", show_alert=True)
        await call.message.delete()
        return

    CHANNEL_USERNAME = "@zdorovkakslon"
    is_subscribed = await check_user_subscription(bot, call.from_user.id, CHANNEL_USERNAME)

    if not is_subscribed:
        await call.answer("Вы всё ещё не подписаны. Попробуйте снова.", show_alert=True)
        return

    # Успешно — идём к отзыву
    await call.message.delete()
    await proceed_to_review(call.message, state, code)
    await call.answer()


async def proceed_to_review(msg: Message, state: FSMContext, code: str):
    """Переход к отзыву после успешной проверки кода и подписки"""
    # Генерируем claim_id и создаём заявку
    claim_id = await Claim.generate_next_claim_id()
    await Claim.create(
        claim_id=claim_id,
        user_id=msg.from_user.id,
        code=code,
        code_status="valid",
        process_status="process",
        claim_status="pending",
        payment_method="unknown"
    )
    await state.update_data(claim_id=claim_id, entered_code=code)

    await msg.answer(
        text=treg.review_request_text,
        reply_markup=tmenu.send_screenshot_ikb()
    )
    await state.set_state(treg.RegState.waiting_for_screenshot)


@router.callback_query(treg.RegCallback.filter())
async def handle_reg_callback(call: CallbackQuery, callback_data: treg.RegCallback, state: FSMContext):
    step = callback_data.step

    if step == "send_screenshot":
        await call.message.edit_text(text=treg.screenshot_request_text)
        await state.set_state(treg.RegState.waiting_for_screenshot)

    elif step == "phone":
        await call.message.edit_text(text=treg.phone_format_text)
        await state.set_state(treg.RegState.waiting_for_phone_number)

    elif step == "card":
        await call.message.edit_text(text=treg.card_format_text)
        await state.set_state(treg.RegState.waiting_for_card_number)

    await call.answer()


@router.message(StateFilter(treg.RegState.waiting_for_screenshot))
async def process_screenshot(msg: Message, state: FSMContext):
    if not msg.photo:
        await msg.answer(text=treg.screenshot_error_text, reply_markup=tmenu.support_ikb())
        return

    user_id = msg.from_user.id
    if user_id not in user_locks:
        user_locks[user_id] = Lock()

    async with user_locks[user_id]:
        data = await state.get_data()
        largest_photo = msg.photo[-1]
        file_id = largest_photo.file_id

        current_photos = data.get("photo_file_ids", [])
        current_photos.append(file_id)

        # Сохраняем данные
        await state.update_data(
            photo_file_ids=current_photos,
            review_text=data.get("review_text", "") or msg.caption or "",
            screenshot_received=True
        )

        # === РЕДАКТИРУЕМ существующее сообщение или создаём новое ===
        existing_msg_id = data.get("phone_card_message_id")

        new_text = f"{treg.phone_or_card_text}"

        if existing_msg_id:
            # Редактируем существующее сообщение
            try:
                await bot.edit_message_text(
                    chat_id=msg.chat.id,
                    message_id=existing_msg_id,
                    text=new_text,
                    reply_markup=tmenu.phone_or_card_ikb()
                )
            except Exception as e:
                if "message is not modified" not in str(e):
                    print(f"Ошибка редактирования: {e}")
        else:
            # Первый раз — отправляем новое сообщение
            sent_msg = await msg.answer(
                text=new_text,
                reply_markup=tmenu.phone_or_card_ikb()
            )
            await state.update_data(phone_card_message_id=sent_msg.message_id)

        await state.set_state(treg.RegState.waiting_for_phone_or_card)

        # Удаляем сообщение пользователя (опционально, для чистоты)
        # try:
        #     await msg.delete()
        # except:
        #     pass

@router.message(StateFilter(treg.RegState.waiting_for_phone_number))
async def process_phone(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if not re.match(r'^(?:\+7|8)\d{10}$', phone):
        await msg.answer("Не похоже на номер телефона. Пожалуйста, укажите номер телефона в формате +7**********")
        return

    await state.update_data(phone=phone)
    await msg.answer(text=treg.bank_request_text)
    await state.set_state(treg.RegState.waiting_for_bank)


@router.message(StateFilter(treg.RegState.waiting_for_card_number))
async def process_card(msg: Message, state: FSMContext):
    card = msg.text.replace(" ", "").strip()
    if not card.isdigit() or len(card) != 16:
        await msg.answer("Не похоже на номер карты. Пожалуйста, укажите номер карты в формате 2222 2222 2222 2222")
        return

    # Сохраняем карту
    await state.update_data(card=card)

    # ❗ Для карты — НЕ запрашиваем банк, сразу завершаем
    await finalize_claim(msg, state)


@router.message(StateFilter(treg.RegState.waiting_for_bank))
async def process_bank(msg: Message, state: FSMContext):
    bank = msg.text.strip()
    await state.update_data(bank=bank)
    await finalize_claim(msg, state)


async def finalize_claim(msg: Message, state: FSMContext):
    """Завершает заявку и отправляет её менеджеру"""
    data = await state.get_data()
    claim_id = data.get("claim_id")  # ← берём из состояния

    if not claim_id:
        # На всякий случай — но не должно происходить
        await msg.answer("Ошибка: заявка не найдена.")
        return

    phone = data.get('phone')
    card = data.get('card')
    bank = data.get('bank', '')

    if phone:
        payment_info = f"Номер телефона: {phone}"
        bank_info = f"Банк: {bank}\n"
    else:
        payment_info = f"Номер карты: {card}"
        bank_info = ""

    claim_text = (
        f"Номер заявки: {claim_id}\n"
        f"Текст: {data.get('review_text', '—')}\n"
        f"{bank_info}"
        f"{payment_info}\n"
        f"Скриншоты:"
    )

    MANAGER_GROUP_ID = 6627225181
    sent_claim = await bot.send_message(
        chat_id=MANAGER_GROUP_ID,
        text=claim_text,
        reply_markup=tadmin.claim_action_ikb(claim_id)
    )

    # Отправка фото
    photo_ids = data.get("photo_file_ids", [])
    if photo_ids:
        if len(photo_ids) == 1:
            await bot.send_photo(chat_id=MANAGER_GROUP_ID, photo=photo_ids[0])
        else:
            media_group = [types.InputMediaPhoto(media=fid) for fid in photo_ids]
            try:
                await bot.send_media_group(chat_id=MANAGER_GROUP_ID, media=media_group)
            except:
                for fid in photo_ids:
                    await bot.send_photo(chat_id=MANAGER_GROUP_ID, photo=fid)

    # === Обновляем заявку в MongoDB ===
    claim = await Claim.get(claim_id=claim_id)
    if claim:
        await claim.update(
            process_status="complete",
            claim_status="confirm",
            payment_method="phone" if phone else "card",
            phone=phone,
            card=card,
            bank=bank if phone else None,
            review_text=data.get('review_text', ''),
            photo_file_ids=photo_ids
        )

    await msg.answer(text=treg.success_text)
    await state.clear()