from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import TARIFFS


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Купить VPN")],
        [KeyboardButton(text="💰 Тарифы"),          KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="💰 Баланс"),           KeyboardButton(text="📤 Вывести деньги")],
        [KeyboardButton(text="📊 Профиль"),          KeyboardButton(text="📋 История")],
        [KeyboardButton(text="❓ FAQ"),              KeyboardButton(text="🏆 Top referal")],
        [KeyboardButton(text="⭐ Baho / Отзыв"),    KeyboardButton(text="🌐 Til / Язык")],
        [KeyboardButton(text="📖 Инструкция"),       KeyboardButton(text="🆘 Поддержка")],
    ], resize_keyboard=True)


def tariffs_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key, tariff in TARIFFS.items():
        rows.append([InlineKeyboardButton(
            text=f"{tariff['name']} — {tariff['price']} ₽",
            callback_data=f"tariff_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СБП",  callback_data=f"sbp_{tariff_id}")],
        [InlineKeyboardButton(text="💎 TON",  callback_data=f"ton_{tariff_id}")],
        [InlineKeyboardButton(text="💎 USDT", callback_data=f"usdt_{tariff_id}")]
    ])


def payment_admin_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{payment_id}"),
        InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"reject_{payment_id}")
    ]])


def withdraw_admin_kb(withdraw_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"wconfirm_{withdraw_id}"),
        InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"wreject_{withdraw_id}")
    ]])


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика",  callback_data="stats"),
         InlineKeyboardButton(text="💳 Платежи",     callback_data="payments")],
        [InlineKeyboardButton(text="📤 Выводы",      callback_data="withdraws"),
         InlineKeyboardButton(text="🎟 Промокоды",   callback_data="promomanage")],
        [InlineKeyboardButton(text="📢 Рассылка",    callback_data="broadcast"),
         InlineKeyboardButton(text="⭐ Отзывы",      callback_data="feedbackstats")],
    ])


def broadcast_target_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем",            callback_data="bc_all")],
        [InlineKeyboardButton(text="✅ Только активным",  callback_data="bc_active")],
        [InlineKeyboardButton(text="❌ Только неактивным",callback_data="bc_inactive")],
    ])


def user_manage_kb(uid: int, banned: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ Разбанить" if banned else "🚫 Забанить"
    ban_data = f"unban_{uid}" if banned else f"ban_{uid}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Дать подписку",   callback_data=f"givesub_{uid}"),
         InlineKeyboardButton(text="💰 Добавить баланс", callback_data=f"givebal_{uid}")],
        [InlineKeyboardButton(text=ban_text, callback_data=ban_data)]
    ])


def instruction_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 iOS",     callback_data="instr_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="instr_android")],
        [InlineKeyboardButton(text="💻 Windows", callback_data="instr_windows")],
        [InlineKeyboardButton(text="🍎 macOS",   callback_data="instr_macos")]
    ])


def back_kb(callback_data: str = "instr_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)
    ]])


def faq_kb(lang: str) -> InlineKeyboardMarkup:
    from lang import t
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'faq_q1'), callback_data="faq_1")],
        [InlineKeyboardButton(text=t(lang, 'faq_q2'), callback_data="faq_2")],
        [InlineKeyboardButton(text=t(lang, 'faq_q3'), callback_data="faq_3")],
        [InlineKeyboardButton(text=t(lang, 'faq_q4'), callback_data="faq_4")],
        [InlineKeyboardButton(text=t(lang, 'faq_q5'), callback_data="faq_5")],
        [InlineKeyboardButton(text=t(lang, 'faq_q6'), callback_data="faq_6")],
        [InlineKeyboardButton(text=t(lang, 'faq_q7'), callback_data="faq_7")],
        [InlineKeyboardButton(text=t(lang, 'faq_q8'), callback_data="faq_8")],
    ])


def feedback_stars_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐",     callback_data="rate_1"),
        InlineKeyboardButton(text="⭐⭐",   callback_data="rate_2"),
        InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate_3"),
        InlineKeyboardButton(text="⭐x4",  callback_data="rate_4"),
        InlineKeyboardButton(text="⭐x5",  callback_data="rate_5"),
    ]])


def language_kb(current_lang: str) -> InlineKeyboardMarkup:
    uz_check = "✅ " if current_lang == 'uz' else ""
    ru_check = "✅ " if current_lang == 'ru' else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{uz_check}🇺🇿 O'zbek", callback_data="setlang_uz")],
        [InlineKeyboardButton(text=f"{ru_check}🇷🇺 Русский", callback_data="setlang_ru")],
    ])


def users_nav_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav])
