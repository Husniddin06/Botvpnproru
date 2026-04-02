import datetime
import aiosqlite

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import DB, TRIAL_DAYS, REF_BONUS, PAYMENT_REF_BONUS, MIN_WITHDRAW, SUPPORT, VPN_LINK, TARIFFS
from database import (
    add_user, get_user, get_balance, create_withdraw, deduct_balance,
    get_user_payments, get_promo_code, use_promo_code, get_user_language,
    set_user_language, save_feedback, get_feedback_stats, has_user_feedback,
    get_referral_leaders, get_user_referral_rank
)
from keyboards import (
    main_menu, tariffs_keyboard, payment_methods_keyboard,
    instruction_kb, back_kb, faq_kb, feedback_stars_kb, language_kb
)
from states import WithdrawStates, PaymentStates, FeedbackStates
from lang import t

router = Router()


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and len(user) > 8 and user[8])


@router.message(CommandStart())
async def start(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы заблокированы.")
        return
    referrer = None
    args = message.text.split()
    if len(args) > 1:
        try:
            ref = int(args[1])
            if ref != message.from_user.id:
                referrer = ref
        except ValueError:
            pass
    await add_user(message.from_user.id, message.from_user.username, referrer)
    user = await get_user(message.from_user.id)
    trial_end = datetime.datetime.fromisoformat(user[5])
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"🎁 Вам доступен бесплатный VPN на <b>{TRIAL_DAYS} дня(дней)</b>.\n"
        f"📅 Активен до: <b>{trial_end.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        "Нажмите кнопку ниже, чтобы подключить VPN.",
        parse_mode="HTML", reply_markup=main_menu())


@router.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu())


@router.message(F.text == "🛒 Купить VPN")
async def buy_vpn(message: types.Message):
    if await is_banned(message.from_user.id):
        return
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id, message.from_user.username)
        user = await get_user(message.from_user.id)
    now = datetime.datetime.now()
    trial_end = datetime.datetime.fromisoformat(user[5])
    if user[6]:
        sub_end = user[7]
        sub_str = datetime.datetime.fromisoformat(sub_end).strftime('%d.%m.%Y') if sub_end else "—"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="🔗 Подключиться", url=VPN_LINK),
            types.InlineKeyboardButton(text="🔄 Продлить",     callback_data="buy_extend")
        ]])
        await message.answer(
            f"✅ Ваша подписка VPN активна!\n"
            f"📅 Действует до: <b>{sub_str}</b>\n\n"
            f"🔗 Ссылка для подключения:\n<code>{VPN_LINK}</code>",
            parse_mode="HTML", reply_markup=kb)
    elif now < trial_end:
        await message.answer(
            f"🎁 У вас активен пробный период!\n"
            f"📅 Действует до: <b>{trial_end.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
            f"🔗 Ссылка для подключения:\n<code>{VPN_LINK}</code>\n\n"
            "Выберите тариф для продления:",
            parse_mode="HTML", reply_markup=tariffs_keyboard())
    else:
        await message.answer(
            "❌ У вас нет активной подписки VPN.\n\nВыберите тариф:",
            reply_markup=tariffs_keyboard())


@router.callback_query(F.data == "buy_extend")
async def buy_extend(callback: types.CallbackQuery):
    await callback.message.answer("🔄 Выберите тариф для продления:",
                                  reply_markup=tariffs_keyboard())
    await callback.answer()


@router.message(F.text == "💰 Тарифы")
async def show_tariffs(message: types.Message):
    text = "📋 <b>Доступные тарифы:</b>\n\n"
    for key, tariff in TARIFFS.items():
        text += f"• {tariff['name']} — <b>{tariff['price']} ₽</b>\n"
    text += "\nДля покупки нажмите «🛒 Купить VPN»."
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())


@router.message(F.text == "👥 Рефералы")
async def referral_info(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (user_id,))
        ref_count = (await cursor.fetchone())[0]
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text="📤 Поделиться",
            url=f"https://t.me/share/url?url={link}&text=Подключайся%20к%20VPN!")
    ]])
    await message.answer(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"🎁 За каждого зарегистрированного друга: <b>{REF_BONUS} ₽</b>\n"
        f"💳 Если друг оплатит подписку: <b>{PAYMENT_REF_BONUS} ₽</b>\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{link}</code>\n\n"
        f"📊 Приглашено друзей: <b>{ref_count}</b>",
        parse_mode="HTML", reply_markup=kb)


@router.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    balance = await get_balance(message.from_user.id)
    await message.answer(
        f"💰 <b>Ваш баланс:</b> {balance} ₽\n"
        f"Минимальная сумма вывода: <b>{MIN_WITHDRAW} ₽</b>",
        parse_mode="HTML", reply_markup=main_menu())


@router.message(F.text == "📊 Профиль")
async def show_profile(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id, message.from_user.username)
        user = await get_user(message.from_user.id)
    user_id  = user[0]
    username = user[1]
    balance  = user[3]
    trial_end= user[5]
    paid     = user[6]
    sub_end  = user[7] if len(user) > 7 else None
    reg_date = user[9] if len(user) > 9 else None
    now = datetime.datetime.now()
    if paid and sub_end:
        sub_end_dt = datetime.datetime.fromisoformat(sub_end)
        days_left  = (sub_end_dt - now).days
        status = (f"✅ Активна до {sub_end_dt.strftime('%d.%m.%Y')} ({days_left} дн.)"
                  if sub_end_dt > now else "❌ Истекла")
    elif now < datetime.datetime.fromisoformat(trial_end):
        trial_end_dt = datetime.datetime.fromisoformat(trial_end)
        days_left    = (trial_end_dt - now).days
        status = f"🎁 Пробный до {trial_end_dt.strftime('%d.%m.%Y')} ({days_left} дн.)"
    else:
        status = "❌ Нет подписки"
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (user_id,))
        ref_count = (await cursor.fetchone())[0]
    reg = datetime.datetime.fromisoformat(reg_date).strftime('%d.%m.%Y') if reg_date else "—"
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔗 Подключиться к VPN", url=VPN_LINK)
    ]]) if paid else None
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Username: @{username or '—'}\n"
        f"📅 Дата регистрации: {reg}\n\n"
        f"📶 Подписка: {status}\n\n"
        f"💰 Баланс: <b>{balance} ₽</b>\n"
        f"👥 Рефералов: <b>{ref_count}</b>",
        parse_mode="HTML", reply_markup=kb or main_menu())


@router.message(F.text == "📋 История")
async def show_history(message: types.Message):
    payments = await get_user_payments(message.from_user.id)
    if not payments:
        await message.answer("📋 <b>История платежей пуста.</b>",
                             parse_mode="HTML", reply_markup=main_menu())
        return
    text = "📋 <b>Последние платежи:</b>\n\n"
    statuses = {"pending": "⏳", "confirmed": "✅", "rejected": "❌"}
    methods  = {"sbp": "СБП", "ton": "TON", "usdt": "USDT"}
    for p in payments:
        pid, uid, tariff, amount, method, screenshot, status = p[0],p[1],p[2],p[3],p[4],p[5],p[6]
        created_at  = p[7] if len(p) > 7 else None
        tariff_name = TARIFFS.get(tariff, {}).get("name", tariff)
        date_str    = datetime.datetime.fromisoformat(created_at).strftime('%d.%m.%Y') if created_at else "—"
        text += (f"{statuses.get(status, '?')} #{pid} | {tariff_name} | "
                 f"{amount} ₽ | {methods.get(method, method)} | {date_str}\n")
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())


@router.message(F.text == "📤 Вывести деньги")
async def withdraw_start(message: types.Message, state: FSMContext):
    balance = await get_balance(message.from_user.id)
    if balance < MIN_WITHDRAW:
        await message.answer(
            f"❌ Недостаточно средств.\n"
            f"Баланс: <b>{balance} ₽</b>\nМинимум: <b>{MIN_WITHDRAW} ₽</b>",
            parse_mode="HTML", reply_markup=main_menu())
        return
    await state.set_state(WithdrawStates.waiting_wallet)
    await message.answer(
        f"💸 <b>Вывод средств</b>\n\n"
        f"Баланс: <b>{balance} ₽</b>\n\n"
        f"Введите адрес кошелька (TON или USDT TRC-20):\n\nДля отмены: /cancel",
        parse_mode="HTML")


@router.message(WithdrawStates.waiting_wallet)
async def withdraw_wallet(message: types.Message, state: FSMContext):
    wallet = message.text.strip()
    if len(wallet) < 10:
        await message.answer("❌ Некорректный адрес кошелька. Попробуйте ещё раз:")
        return
    await state.update_data(wallet=wallet)
    await state.set_state(WithdrawStates.waiting_amount)
    balance = await get_balance(message.from_user.id)
    await message.answer(f"Введите сумму для вывода (от {MIN_WITHDRAW} до {balance} ₽):")


@router.message(WithdrawStates.waiting_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите целое число.")
        return
    balance = await get_balance(message.from_user.id)
    if amount > balance:
        await message.answer(f"❌ Недостаточно средств. Баланс: {balance} ₽")
        return
    if amount < MIN_WITHDRAW:
        await message.answer(f"❌ Минимальная сумма: {MIN_WITHDRAW} ₽")
        return
    data   = await state.get_data()
    wallet = data["wallet"]
    from config import ADMIN_ID
    from keyboards import withdraw_admin_kb
    withdraw_id = await create_withdraw(message.from_user.id, amount, wallet)
    await deduct_balance(message.from_user.id, amount)
    await message.bot.send_message(ADMIN_ID,
        f"💸 <b>Новая заявка на вывод!</b>\n\n"
        f"🆔 Заявка #{withdraw_id}\n"
        f"👤 @{message.from_user.username} (ID: {message.from_user.id})\n"
        f"💰 Сумма: <b>{amount} ₽</b>\n"
        f"💳 Кошелёк: <code>{wallet}</code>",
        parse_mode="HTML", reply_markup=withdraw_admin_kb(withdraw_id))
    await state.clear()
    await message.answer(
        f"✅ Заявка принята!\n"
        f"Сумма: <b>{amount} ₽</b>\n"
        f"Кошелёк: <code>{wallet}</code>\n\n"
        f"Обработаем в ближайшее время.",
        parse_mode="HTML", reply_markup=main_menu())


@router.message(F.text == "📖 Инструкция")
async def instruction(message: types.Message):
    await message.answer(
        "📖 <b>Инструкция по подключению VPN</b>\n\nВыберите вашу платформу:",
        parse_mode="HTML", reply_markup=instruction_kb())


@router.callback_query(F.data == "instr_ios")
async def instr_ios(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📱 <b>Инструкция для iOS</b>\n\n"
        "1️⃣ Скачайте <b>V2Box</b> или <b>Shadowrocket</b> из App Store\n"
        "2️⃣ Нажмите «🛒 Купить VPN» и оформите подписку\n"
        "3️⃣ После активации скопируйте ссылку для подключения\n"
        "4️⃣ В приложении нажмите «+» → «Импорт из буфера обмена»\n"
        "5️⃣ Нажмите «Подключить» и разрешите VPN-конфигурацию\n\n"
        f"❓ Поддержка: {SUPPORT}",
        parse_mode="HTML", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "instr_android")
async def instr_android(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🤖 <b>Инструкция для Android</b>\n\n"
        "1️⃣ Скачайте <b>V2RayNG</b> из Google Play или APKPure\n"
        "2️⃣ Нажмите «🛒 Купить VPN» и оформите подписку\n"
        "3️⃣ После активации скопируйте ссылку для подключения\n"
        "4️⃣ В V2RayNG нажмите «+» → «Импорт из буфера обмена»\n"
        "5️⃣ Нажмите кнопку запуска (треугольник)\n\n"
        f"❓ Поддержка: {SUPPORT}",
        parse_mode="HTML", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "instr_windows")
async def instr_windows(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💻 <b>Инструкция для Windows</b>\n\n"
        "1️⃣ Скачайте <b>V2RayN</b> с GitHub (github.com/2dust/v2rayN)\n"
        "2️⃣ Нажмите «🛒 Купить VPN» и оформите подписку\n"
        "3️⃣ После активации скопируйте ссылку для подключения\n"
        "4️⃣ V2RayN: Серверы → Импорт из буфера обмена\n"
        "5️⃣ Выберите сервер и нажмите «Запустить»\n\n"
        f"❓ Поддержка: {SUPPORT}",
        parse_mode="HTML", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "instr_macos")
async def instr_macos(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🍎 <b>Инструкция для macOS</b>\n\n"
        "1️⃣ Скачайте <b>V2Box</b> из Mac App Store\n"
        "2️⃣ Нажмите «🛒 Купить VPN» и оформите подписку\n"
        "3️⃣ После активации скопируйте ссылку для подключения\n"
        "4️⃣ V2Box: нажмите «+» → «Вставить из буфера обмена»\n"
        "5️⃣ Нажмите «Подключить»\n\n"
        f"❓ Поддержка: {SUPPORT}",
        parse_mode="HTML", reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "instr_back")
async def instr_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 <b>Инструкция по подключению VPN</b>\n\nВыберите вашу платформу:",
        parse_mode="HTML", reply_markup=instruction_kb())
    await callback.answer()


@router.message(F.text == "🆘 Поддержка")
async def support(message: types.Message):
    await message.answer(
        f"🆘 <b>Поддержка</b>\n\nОбратитесь к администратору:\n\n👤 {SUPPORT}",
        parse_mode="HTML", reply_markup=main_menu())


# ============ FAQ ============

@router.message(F.text == "❓ FAQ")
async def faq_menu(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(t(lang, 'faq_title'), parse_mode="HTML", reply_markup=faq_kb(lang))


@router.callback_query(F.data.startswith("faq_"))
async def faq_answer(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    num  = callback.data.split("_")[1]
    key  = f"faq_a{num}"
    text = t(lang, key)
    back = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text=t(lang, 'faq_back'), callback_data="faq_back")
    ]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back)
    await callback.answer()


@router.callback_query(F.data == "faq_back")
async def faq_back(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        t(lang, 'faq_title'), parse_mode="HTML", reply_markup=faq_kb(lang))
    await callback.answer()


# ============ TOP REFERRAL ============

@router.message(F.text == "🏆 Top referal")
async def top_referral(message: types.Message):
    lang    = await get_user_language(message.from_user.id)
    leaders = await get_referral_leaders(10)
    if not leaders:
        await message.answer(t(lang, 'leaderboard_empty'), reply_markup=main_menu())
        return
    text = t(lang, 'leaderboard_title')
    for i, (uid, username, count) in enumerate(leaders, start=1):
        text += t(lang, 'leaderboard_row',
                  pos=i, username=username or str(uid), count=count)
    rank, my_count = await get_user_referral_rank(message.from_user.id)
    text += t(lang, 'leaderboard_you', pos=rank, count=my_count)
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())


# ============ FEEDBACK ============

@router.message(F.text == "⭐ Baho / Отзыв")
async def feedback_start(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    if await has_user_feedback(message.from_user.id):
        stats = await get_feedback_stats()
        avg_str = str(stats['avg']) if stats['avg'] else "—"
        await message.answer(
            t(lang, 'feedback_already') + "\n\n" +
            t(lang, 'feedback_stats', avg=avg_str, count=stats['count']),
            parse_mode="HTML", reply_markup=main_menu())
        return
    await message.answer(
        t(lang, 'feedback_title'), parse_mode="HTML",
        reply_markup=feedback_stars_kb())


@router.callback_query(F.data.startswith("rate_"))
async def feedback_rate(callback: types.CallbackQuery, state: FSMContext):
    lang   = await get_user_language(callback.from_user.id)
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await state.set_state(FeedbackStates.waiting_comment)
    stars  = "⭐" * rating
    await callback.message.edit_text(
        f"{stars}\n\n" + t(lang, 'feedback_comment'), parse_mode="HTML")
    await callback.answer()


@router.message(FeedbackStates.waiting_comment)
async def feedback_comment(message: types.Message, state: FSMContext):
    lang    = await get_user_language(message.from_user.id)
    data    = await state.get_data()
    rating  = data.get("rating", 5)
    comment = None if message.text.strip() == "/skip" else message.text.strip()
    await save_feedback(message.from_user.id, rating, comment)
    await state.clear()
    from config import ADMIN_ID
    stars = "⭐" * rating
    try:
        await message.bot.send_message(ADMIN_ID,
            f"⭐ <b>Новый отзыв!</b>\n\n"
            f"👤 @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"Оценка: {stars} ({rating}/5)\n"
            f"Комментарий: {comment or '—'}",
            parse_mode="HTML")
    except Exception:
        pass
    await message.answer(t(lang, 'feedback_done'), reply_markup=main_menu())


# ============ LANGUAGE ============

@router.message(F.text == "🌐 Til / Язык")
async def language_menu(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        t(lang, 'lang_current'), reply_markup=language_kb(lang))


@router.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    new_lang = callback.data.split("_")[1]
    await set_user_language(callback.from_user.id, new_lang)
    await callback.message.edit_text(
        t(new_lang, 'lang_selected'), reply_markup=language_kb(new_lang))
    await callback.answer()
