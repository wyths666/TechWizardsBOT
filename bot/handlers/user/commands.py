from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import re
from bot.templates.user import reg as treg
from bot.templates.user import menu as tmenu  # ← добавлено
from bot.filters.user import NewUser
from core.bot import bot
from utils.check_subscribe import check_user_subscription

router = Router()




# Заглушка: валидные коды (в реальном проекте — из БД)
VALID_CODES = {"ABC123", "XYZ789"}

# @router.message(Command("start"))
# async def menu(msg: types.Message, state: FSMContext):
#     """ /start для вызова меню (для уже зарегистрированных) """
#     await msg.answer(text=tmenu.menu_text, reply_markup=tmenu.menu_ikb())
#     await msg.delete()


@router.message(Command("start"), NewUser())
async def start_new_user(msg: Message, state: FSMContext):
    await msg.answer(text=treg.start_text)
    await state.set_state(treg.RegState.waiting_for_code)
    await msg.delete()


@router.message(StateFilter(treg.RegState.waiting_for_code))
async def process_code(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()

    if code not in VALID_CODES:
        await msg.answer(text=treg.code_not_found_text, reply_markup=tmenu.support_ikb())
        return

    # VALID_CODES.remove(code)

    # === Сначала показываем сообщение о выигрыше ===
    await msg.answer(text=treg.code_found_text)
    await state.update_data(entered_code=code)

    # === Затем проверяем подписку ===
    CHANNEL_USERNAME = "@tech_repost"
    is_subscribed = await check_user_subscription(bot, msg.from_user.id, CHANNEL_USERNAME)

    if not is_subscribed:
        await msg.answer(
            text=treg.not_subscribed_text,
            reply_markup=tmenu.check_subscription_ikb()
        )
        return

    # === Если подписан — просим отзыв ===
    await msg.answer(text=treg.review_request_text, reply_markup=tmenu.send_screenshot_ikb())
    await state.set_state(treg.RegState.waiting_for_screenshot)


@router.callback_query(treg.RegCallback.filter(F.step == "check_sub"))
async def check_subscription_callback(call: CallbackQuery, state: FSMContext):
    # Получаем текущий код из состояния
    data = await state.get_data()
    code = data.get("entered_code")

    if not code:
        await call.answer("Сессия устарела. Пожалуйста, введите код снова.", show_alert=True)
        await call.message.delete()
        return

    # Проверяем подписку
    CHANNEL_USERNAME = "@tech_repost"
    is_subscribed = await check_user_subscription(bot, call.from_user.id, CHANNEL_USERNAME)

    if not is_subscribed:
        await call.answer("Вы всё ещё не подписаны. Попробуйте снова.", show_alert=True)
        return

    # Если подписан — удаляем сообщение с кнопкой и идём дальше
    await call.message.delete()

    await call.message.answer(
        text=treg.review_request_text,
        reply_markup=tmenu.send_screenshot_ikb()
    )
    await state.set_state(treg.RegState.waiting_for_screenshot)
    await call.answer()


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


from asyncio import Lock

# Создаем лок для каждого пользователя
user_locks = {}

from asyncio import Lock

# Создаем лок для каждого пользователя
user_locks = {}


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

        new_text = f"📸 Добавлено скриншотов: {len(current_photos)}\n\n{treg.phone_or_card_text}"

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

    await state.update_data(card=card)
    await msg.answer(text=treg.bank_request_text)
    await state.set_state(treg.RegState.waiting_for_bank)


@router.message(StateFilter(treg.RegState.waiting_for_bank))
async def process_bank(msg: Message, state: FSMContext):
    bank = msg.text.strip()
    await state.update_data(bank=bank)

    data = await state.get_data()
    code = data.get("entered_code")

    if code in VALID_CODES:
        VALID_CODES.remove(code)

    # Формируем текст заявки
    claim_text = (
        f"📌 Новая заявка на выигрыш!\n"
        f"👤 Пользователь: t.me/user/{msg.from_user.id}\n"
        f"📝 Отзыв: {data.get('review_text', '—')}\n"
        f"🏦 Банк: {bank}\n"
        f"📞 Телефон: {data.get('phone', '—')}\n"
        f"💳 Карта: {data.get('card', '—')}"
    )

    MANAGER_GROUP_ID = 808947863
    await bot.send_message(MANAGER_GROUP_ID, claim_text)

    photo_ids = data.get("photo_file_ids", [])
    photos_sent = data.get("photos_sent_to_manager", False)

    # ✅ ИСПРАВЛЕННАЯ отправка фото
    if photo_ids and not photos_sent:
        # Если фото только одно
        if len(photo_ids) == 1:
            await bot.send_photo(
                chat_id=MANAGER_GROUP_ID,
                photo=photo_ids[0],
                caption="🖼️ Скриншот отзыва"
            )
        # Если фото несколько - отправляем медиагруппу
        else:
            media_group = []
            for i, file_id in enumerate(photo_ids):
                # Только у первого фото будет caption
                if i == 0:
                    media_group.append(
                        types.InputMediaPhoto(
                            media=file_id,
                            caption="🖼️ Скриншоты отзыва"
                        )
                    )
                else:
                    media_group.append(
                        types.InputMediaPhoto(media=file_id)
                    )

            try:
                await bot.send_media_group(
                    chat_id=MANAGER_GROUP_ID,
                    media=media_group
                )
            except Exception as e:
                print(f"Ошибка отправки медиагруппы: {e}")
                # Fallback: отправляем по одному
                for file_id in photo_ids:
                    await bot.send_photo(
                        chat_id=MANAGER_GROUP_ID,
                        photo=file_id
                    )

        # ✅ Помечаем, что фото отправлены
        await state.update_data(photos_sent_to_manager=True)

    await msg.answer(text=treg.success_text)
    await state.clear()


