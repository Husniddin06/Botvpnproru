import asyncio
import datetime

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import TARIFFS, SBP_LINK, TON_WALLET, USDT_WALLET, PAYMENT_REF_BONUS, ADMIN_ID
from database import (
    add_payment, get_payment_by_id, confirm_payment, reject_payment,
    activate_vpn, get_user, add_balance, get_user_payments,
    get_promo_code, use_promo_code
)
from keyboards import (
    main_menu, tariffs_keyboard, payment_methods_keyboard,
    payment_admin_kb, admin_panel_kb
)
from states import PaymentStates

router = Router()


@router.callback_query(F.data.startswith("tariff_"))
async def tariff_selected(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден")
        return
    await state.update_data(tariff_id=tariff_id, amount=tariff["price"])
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎟 Ввести промокод",
                                    callback_data=f"enterpromo_{tariff_id}")],
        [types.InlineKeyboardButton(text="➡️ Продолжить без промокода",
                                    callback_data=f"skippromo_{tariff_id}")]
    ])
    await callback.message.edit_text(
        f"✅ Вы выбрали: <b>{tariff['name']}</b>\n"
        f"💰 Стоимость: <b>{tariff['price']} ₽</b>\n\nЕсть промокод?",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("enterpromo_"))
async def enter_promo(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_promo)
    await callback.message.edit_text("🎟 Введите промокод:")
    await callback.answer()


@router.message(PaymentStates.waiting_promo)
async def check_promo(message: types.Message, state: FSMContext):
    code      = message.text.strip()
    promo     = await get_promo_code(code)
    data      = await state.get_data()
    tariff_id = data.get("tariff_id")
    tariff    = TARIFFS.get(tariff_id)
    if not tariff:
        await state.clear()
        await message.answer("❌ Сессия устарела. Начните заново.", reply_markup=main_menu())
        return
    if not promo:
        await state.update_data(amount=tariff["price"])
        await state.set_state(None)
        await message.answer(
            "❌ Промокод недействителен или исчерпан.\n\nВыберите способ оплаты:",
            reply_markup=payment_methods_keyboard(tariff_id))
        return
    discount  = promo[1]
    new_price = max(1, tariff["price"] - discount)
    await use_promo_code(code)
    await state.update_data(amount=new_price)
    await state.set_state(None)
    await message.answer(
        f"✅ Промокод применён! Скидка: <b>{discount} ₽</b>\n"
        f"💰 Итоговая цена: <b>{new_price} ₽</b>\n\nВыберите способ оплаты:",
        parse_mode="HTML", reply_markup=payment_methods_keyboard(tariff_id))


@router.callback_query(F.data.startswith("skippromo_"))
async def skip_promo(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    tariff    = TARIFFS.get(tariff_id)
    await state.update_data(tariff_id=tariff_id, amount=tariff["price"])
    await callback.message.edit_text(
        f"✅ Вы выбрали: <b>{tariff['name']}</b>\n"
        f"💰 Стоимость: <b>{tariff['price']} ₽</b>\n\nВыберите способ оплаты:",
        parse_mode="HTML", reply_markup=payment_methods_keyboard(tariff_id))
    await callback.answer()


@router.callback_query(F.data.startswith("sbp_"))
async def payment_sbp(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    data   = await state.get_data()
    amount = data.get("amount", TARIFFS.get(tariff_id, {}).get("price"))
    await state.update_data(tariff_id=tariff_id, method="sbp", amount=amount)
    await state.set_state(PaymentStates.waiting_screenshot)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="💳 Перейти к оплате через СБП", url=SBP_LINK)
    ]])
    await callback.message.edit_text(
        f"💳 <b>Оплата через СБП</b>\n\n"
        f"Сумма: <b>{amount} ₽</b>\n\n"
        f"Нажмите кнопку ниже для перехода к оплате.\n\n"
        f"После оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("ton_"))
async def payment_ton(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    data   = await state.get_data()
    amount = data.get("amount", TARIFFS.get(tariff_id, {}).get("price"))
    await state.update_data(tariff_id=tariff_id, method="ton", amount=amount)
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.edit_text(
        f"💎 <b>Оплата через TON</b>\n\n"
        f"Сумма: <b>{amount} ₽</b> (в эквиваленте TON)\n\n"
        f"📬 Адрес TON кошелька:\n<code>{TON_WALLET}</code>\n\n"
        f"После оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("usdt_"))
async def payment_usdt(callback: types.CallbackQuery, state: FSMContext):
    tariff_id = callback.data.split("_")[1]
    data   = await state.get_data()
    amount = data.get("amount", TARIFFS.get(tariff_id, {}).get("price"))
    await state.update_data(tariff_id=tariff_id, method="usdt", amount=amount)
    await state.set_state(PaymentStates.waiting_screenshot)
    await callback.message.edit_text(
        f"💎 <b>Оплата через USDT (TRC-20)</b>\n\n"
        f"Сумма: <b>{amount} ₽</b> (в эквиваленте USDT)\n\n"
        f"📬 Адрес USDT кошелька:\n<code>{USDT_WALLET}</code>\n\n"
        f"После оплаты отправьте <b>скриншот чека</b>:",
        parse_mode="HTML")
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: types.Message, state: FSMContext):
    data   = await state.get_data()
    tariff = TARIFFS.get(data.get("tariff_id", ""))
    if not tariff:
        await state.clear()
        await message.answer("❌ Сессия устарела. Начните заново.", reply_markup=main_menu())
        return
    photo_id   = message.photo[-1].file_id
    payment_id = await add_payment(
        message.from_user.id, data["tariff_id"], data["amount"], data["method"], photo_id)
    methods = {"sbp": "СБП", "ton": "TON", "usdt": "USDT (TRC-20)"}
    await message.bot.send_photo(ADMIN_ID, photo=photo_id,
        caption=(
            f"💳 <b>Новая заявка на оплату!</b>\n\n"
            f"🆔 ID платежа: #{payment_id}\n"
            f"👤 @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"📦 Тариф: {tariff['name']}\n"
            f"💰 Сумма: {data['amount']} ₽\n"
            f"💳 Способ: {methods.get(data['method'], data['method'])}"),
        parse_mode="HTML", reply_markup=payment_admin_kb(payment_id))
    await state.clear()
    await message.answer(
        "✅ <b>Чек отправлен!</b>\n\n"
        "Администратор активирует подписку в течение 5–15 минут.",
        parse_mode="HTML", reply_markup=main_menu())


@router.message(PaymentStates.waiting_screenshot)
async def wrong_screenshot(message: types.Message):
    await message.answer("📸 Пожалуйста, отправьте <b>фото</b> чека об оплате.", parse_mode="HTML")


@router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_payment(callback: types.CallbackQuery):
    from config import ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    payment_id = int(callback.data.split("_")[1])
    payment    = await get_payment_by_id(payment_id)
    if not payment:
        await callback.answer("Платёж не найден.", show_alert=True)
        return
    if payment[6] != "pending":
        await callback.answer("Платёж уже обработан.", show_alert=True)
        return
    user_id   = payment[1]
    tariff_id = payment[2]
    tariff    = TARIFFS.get(tariff_id, {})
    days      = tariff.get("days", 30)
    new_end   = await activate_vpn(user_id, days)
    await confirm_payment(payment_id)
    referrer = await get_user(user_id)
    if referrer and referrer[2]:
        await add_balance(referrer[2], PAYMENT_REF_BONUS)
    from config import VPN_LINK
    try:
        await callback.bot.send_message(user_id,
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"📦 Тариф: {tariff.get('name', tariff_id)}\n"
            f"📅 Действует до: <b>{new_end.strftime('%d.%m.%Y')}</b>\n\n"
            f"🔗 Ссылка для подключения:\n<code>{VPN_LINK}</code>",
            parse_mode="HTML")
    except Exception:
        pass
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML")
    await callback.answer("Подписка активирована!")


@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_payment(callback: types.CallbackQuery):
    from config import ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    payment_id = int(callback.data.split("_")[1])
    payment    = await get_payment_by_id(payment_id)
    if not payment:
        await callback.answer("Платёж не найден.", show_alert=True)
        return
    if payment[6] != "pending":
        await callback.answer("Платёж уже обработан.", show_alert=True)
        return
    user_id = payment[1]
    await reject_payment(payment_id)
    try:
        await callback.bot.send_message(user_id,
            "❌ <b>Ваш платёж отклонён.</b>\n\n"
            "Пожалуйста, свяжитесь с поддержкой, если считаете это ошибкой.",
            parse_mode="HTML")
    except Exception:
        pass
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML")
    await callback.answer("Платёж отклонён.")
