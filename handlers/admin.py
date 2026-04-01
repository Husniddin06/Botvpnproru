import asyncio
import datetime
import io
import aiosqlite

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, DB, TARIFFS, VPN_LINK
from database import (
    get_user, get_all_users, get_active_user_ids, get_inactive_user_ids,
    get_stats, ban_user, unban_user, activate_vpn, add_balance, add_promo_code,
    get_pending_payments, get_payment_by_id, get_withdraw_by_id,
    confirm_withdraw, reject_withdraw, restore_balance_withdraw,
    get_users_count, get_users_paginated, search_user_by_username,
    get_feedback_stats
)
from keyboards import (
    admin_panel_kb, user_manage_kb, payment_admin_kb,
    withdraw_admin_kb, broadcast_target_kb, users_nav_kb
)
from states import BroadcastStates, AdminStates
from lang import t

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа.")
        return
    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\nВыберите раздел:",
        parse_mode="HTML", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    s = await get_stats()
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Всего пользователей: <b>{s['total']}</b>\n"
        f"🆕 Новых сегодня: <b>{s['new_today']}</b>\n"
        f"📅 Новых в этом месяце: <b>{s['new_month']}</b>\n"
        f"🚫 Заблокировано: <b>{s['banned']}</b>\n\n"
        f"✅ С активной подпиской: <b>{s['paid']}</b>\n\n"
        f"⏳ Ожидают подтверждения: <b>{s['pending']}</b>\n"
        f"✅ Подтверждённых платежей: <b>{s['confirmed']}</b>\n"
        f"💰 Доход за сегодня: <b>{s['income_today']} ₽</b>\n"
        f"💰 Общий доход: <b>{s['income']} ₽</b>",
        parse_mode="HTML", reply_markup=admin_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "feedbackstats")
async def show_feedback_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    stats = await get_feedback_stats()
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT u.username, f.rating, f.comment, f.created_at "
            "FROM feedback f JOIN users u ON u.user_id=f.user_id "
            "ORDER BY f.created_at DESC LIMIT 10")
        rows = await cursor.fetchall()
    avg_str = str(stats['avg']) if stats['avg'] else "—"
    text = (f"⭐ <b>Отзывы пользователей</b>\n\n"
            f"📊 Средний рейтинг: <b>{avg_str}/5</b> ({stats['count']} отзывов)\n\n")
    for username, rating, comment, created_at in rows:
        stars = "⭐" * rating
        date  = created_at[:10] if created_at else "—"
        text += f"@{username or '?'} {stars} {date}\n"
        if comment:
            text += f"   💬 {comment}\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "payments")
async def show_payments(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    payments = await get_pending_payments()
    if not payments:
        await callback.message.edit_text("💳 Ожидающих платежей нет.",
                                         reply_markup=admin_panel_kb())
    else:
        await callback.message.edit_text(
            f"💳 <b>Ожидающих платежей: {len(payments)}</b>\n\nЧеки отправлены ниже.",
            parse_mode="HTML", reply_markup=admin_panel_kb())
        for p in payments:
            try:
                await callback.bot.send_photo(
                    callback.from_user.id,
                    photo=p[5],
                    caption=(
                        f"🆔 #{p[0]} | 👤 ID: {p[1]}\n"
                        f"📦 {TARIFFS.get(p[2], {}).get('name', p[2])} | "
                        f"💰 {p[3]} ₽ | {p[4]}"),
                    reply_markup=payment_admin_kb(p[0]))
            except Exception:
                pass
    await callback.answer()


@router.callback_query(F.data == "withdraws")
async def show_withdraws(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT * FROM withdraws WHERE status='pending' ORDER BY id DESC")
        withdraws = await cursor.fetchall()
    if not withdraws:
        await callback.message.edit_text("📤 Заявок на вывод нет.",
                                         reply_markup=admin_panel_kb())
    else:
        await callback.message.edit_text(
            f"📤 <b>Заявок на вывод: {len(withdraws)}</b>\n\nЗаявки отправлены ниже.",
            parse_mode="HTML", reply_markup=admin_panel_kb())
        for w in withdraws:
            date_str = w[5][:10] if len(w) > 5 and w[5] else "—"
            try:
                await callback.bot.send_message(
                    callback.from_user.id,
                    f"💸 <b>Заявка на вывод #{w[0]}</b>\n\n"
                    f"👤 ID: {w[1]}\n"
                    f"💰 Сумма: <b>{w[2]} ₽</b>\n"
                    f"💳 Кошелёк: <code>{w[3]}</code>\n"
                    f"📅 Дата: {date_str}",
                    parse_mode="HTML",
                    reply_markup=withdraw_admin_kb(w[0]))
            except Exception:
                pass
    await callback.answer()


@router.callback_query(F.data.startswith("wconfirm_"))
async def admin_confirm_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    withdraw_id = int(callback.data.split("_")[1])
    withdraw    = await get_withdraw_by_id(withdraw_id)
    if not withdraw:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if withdraw[4] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await confirm_withdraw(withdraw_id)
    user_id = withdraw[1]
    amount  = withdraw[2]
    wallet  = withdraw[3]
    lang    = "ru"
    try:
        from database import get_user_language
        lang = await get_user_language(user_id)
    except Exception:
        pass
    try:
        await callback.bot.send_message(user_id,
            t(lang, 'withdraw_user_ok', amount=amount, wallet=wallet),
            parse_mode="HTML")
    except Exception:
        pass
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML")
    await callback.answer(t('ru', 'withdraw_confirmed', id=withdraw_id))


@router.callback_query(F.data.startswith("wreject_"))
async def admin_reject_withdraw(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    withdraw_id = int(callback.data.split("_")[1])
    withdraw    = await get_withdraw_by_id(withdraw_id)
    if not withdraw:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if withdraw[4] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await reject_withdraw(withdraw_id)
    await restore_balance_withdraw(withdraw_id)
    user_id = withdraw[1]
    lang    = "ru"
    try:
        from database import get_user_language
        lang = await get_user_language(user_id)
    except Exception:
        pass
    try:
        await callback.bot.send_message(user_id,
            t(lang, 'withdraw_user_no'), parse_mode="HTML")
    except Exception:
        pass
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО (баланс возвращён)</b>",
        parse_mode="HTML")
    await callback.answer(t('ru', 'withdraw_rejected', id=withdraw_id))


@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_target)
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\nКому отправить сообщение?",
        parse_mode="HTML", reply_markup=broadcast_target_kb())
    await callback.answer()


@router.callback_query(F.data.in_({"bc_all", "bc_active", "bc_inactive"}))
async def broadcast_choose_target(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    labels = {"bc_all": "Всем", "bc_active": "Только активным", "bc_inactive": "Только неактивным"}
    await state.update_data(broadcast_target=callback.data)
    await state.set_state(BroadcastStates.waiting_message)
    await callback.message.answer(
        f"✅ Цель: <b>{labels[callback.data]}</b>\n\nВведите текст сообщения:",
        parse_mode="HTML")
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def do_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data   = await state.get_data()
    target = data.get("broadcast_target", "bc_all")
    if target == "bc_active":
        users = await get_active_user_ids()
    elif target == "bc_inactive":
        users = await get_inactive_user_ids()
    else:
        users = await get_all_users()
    sent, failed = 0, 0
    for uid in users:
        try:
            await message.bot.send_message(
                uid,
                f"📢 <b>Сообщение от администратора:</b>\n\n{message.text}",
                parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await state.clear()
    await message.answer(
        f"✅ Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


@router.callback_query(F.data == "promomanage")
async def promo_manage(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_promo_code)
    await callback.message.answer("🎟 Создание промокода.\n\nВведите код (например: SALE20):")
    await callback.answer()


@router.message(AdminStates.waiting_promo_code)
async def promo_get_code(message: types.Message, state: FSMContext):
    await state.update_data(promo_code=message.text.strip().upper())
    await state.set_state(AdminStates.waiting_promo_discount)
    await message.answer("Введите размер скидки в рублях (например: 20):")


@router.message(AdminStates.waiting_promo_discount)
async def promo_get_discount(message: types.Message, state: FSMContext):
    try:
        discount = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    await state.update_data(promo_discount=discount)
    await state.set_state(AdminStates.waiting_promo_uses)
    await message.answer("Введите количество использований:")


@router.message(AdminStates.waiting_promo_uses)
async def promo_get_uses(message: types.Message, state: FSMContext):
    try:
        uses = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    data = await state.get_data()
    await add_promo_code(data["promo_code"], data["promo_discount"], uses)
    await state.clear()
    await message.answer(
        f"✅ Промокод создан!\n\n"
        f"🎟 Код: <code>{data['promo_code']}</code>\n"
        f"💰 Скидка: {data['promo_discount']} ₽\n"
        f"🔢 Использований: {uses}",
        parse_mode="HTML")


@router.message(Command("user"))
async def manage_user_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /user <ID>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID.")
        return
    user = await get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    await _send_user_info(message, user)


@router.message(Command("find"))
async def find_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /find @username")
        return
    user = await search_user_by_username(args[1])
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    await _send_user_info(message, user)


async def _send_user_info(message: types.Message, user):
    uid      = user[0]
    username = user[1]
    balance  = user[3]
    paid     = user[6]
    sub_end  = user[7] if len(user) > 7 else None
    banned   = bool(user[8]) if len(user) > 8 else False
    if paid and sub_end:
        sub_end_dt = datetime.datetime.fromisoformat(sub_end)
        sub_status = f"✅ до {sub_end_dt.strftime('%d.%m.%Y')}"
    else:
        sub_status = "❌ Нет подписки"
    banned_str = "🚫 Заблокирован" if banned else "✅ Активен"
    await message.answer(
        f"👤 Пользователь: @{username or '—'} (ID: {uid})\n"
        f"💰 Баланс: {balance} ₽\n"
        f"📦 Подписка: {sub_status}\n"
        f"🔒 Статус: {banned_str}",
        reply_markup=user_manage_kb(uid, banned))


@router.message(Command("users"))
async def list_users(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await _send_users_page(message, 0)


@router.callback_query(F.data.startswith("users_page_"))
async def users_page(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page = int(callback.data.split("_")[2])
    await _send_users_page(callback.message, page, edit=True)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


async def _send_users_page(message: types.Message, page: int, edit: bool = False):
    per_page    = 10
    total       = await get_users_count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(0, min(page, total_pages - 1))
    users       = await get_users_paginated(page * per_page, per_page)
    text        = f"👥 <b>Пользователи</b> (стр. {page+1}/{total_pages})\n\n"
    statuses    = {(True, False): "✅", (False, False): "🔘", (False, True): "🚫", (True, True): "🚫"}
    for u in users:
        uid, username, paid, banned, reg_date = u
        s    = statuses.get((bool(paid), bool(banned)), "🔘")
        date = reg_date[:10] if reg_date else "—"
        text += f"{s} <code>{uid}</code> @{username or '—'} {date}\n"
    kb = users_nav_kb(page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(Command("backup"))
async def backup_db(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        with open(DB, "rb") as f:
            data = f.read()
        buf = io.BytesIO(data)
        buf.name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        await message.answer_document(
            types.BufferedInputFile(data, filename=buf.name),
            caption=f"💾 Резервная копия базы данных\n📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка создания резервной копии: {e}")


@router.callback_query(F.data.startswith("ban_"))
async def admin_ban(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[1])
    await ban_user(uid)
    await callback.answer("Пользователь заблокирован.")
    await callback.message.edit_text(f"🚫 Пользователь {uid} заблокирован.")


@router.callback_query(F.data.startswith("unban_"))
async def admin_unban(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[1])
    await unban_user(uid)
    await callback.answer("Пользователь разблокирован.")
    await callback.message.edit_text(f"✅ Пользователь {uid} разблокирован.")


@router.callback_query(F.data.startswith("givesub_"))
async def admin_give_sub(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[1])
    await state.update_data(target_uid=uid)
    await state.set_state(AdminStates.waiting_give_sub)
    await callback.message.answer(f"Введите количество дней подписки для пользователя {uid}:")
    await callback.answer()


@router.message(AdminStates.waiting_give_sub)
async def admin_give_sub_days(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    data    = await state.get_data()
    uid     = data["target_uid"]
    new_end = await activate_vpn(uid, days)
    await state.clear()
    try:
        await message.bot.send_message(uid,
            f"🎁 <b>Администратор выдал вам подписку!</b>\n\n"
            f"📅 Действует до: <b>{new_end.strftime('%d.%m.%Y')}</b>\n\n"
            f"🔗 Ссылка:\n<code>{VPN_LINK}</code>",
            parse_mode="HTML")
    except Exception:
        pass
    await message.answer(f"✅ Подписка на {days} дней выдана пользователю {uid}.")


@router.callback_query(F.data.startswith("givebal_"))
async def admin_give_bal(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[1])
    await state.update_data(target_uid=uid)
    await state.set_state(AdminStates.waiting_give_bal)
    await callback.message.answer(f"Введите сумму баланса для пользователя {uid} (в рублях):")
    await callback.answer()


@router.message(AdminStates.waiting_give_bal)
async def admin_give_bal_amount(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    data   = await state.get_data()
    uid    = data["target_uid"]
    await add_balance(uid, amount)
    await state.clear()
    try:
        await message.bot.send_message(uid,
            f"💰 <b>Администратор пополнил ваш баланс на {amount} ₽!</b>",
            parse_mode="HTML")
    except Exception:
        pass
    await message.answer(f"✅ Баланс пользователя {uid} пополнен на {amount} ₽.")
