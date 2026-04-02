import asyncio
import datetime
import logging

from aiogram import Bot

from database import deactivate_expired, get_expiring_users, get_stats
from config import ADMIN_ID

logger = logging.getLogger(__name__)


async def scheduler(bot: Bot):
    last_daily_report = None
    notified_expiring: dict[int, set] = {}

    while True:
        try:
            now = datetime.datetime.now()
            today = now.date()

            # Muddati o'tgan obunalarni o'chirish / Деактивация истёкших подписок
            expired = await deactivate_expired()
            for uid in expired:
                notified_expiring.pop(uid, None)
                try:
                    await bot.send_message(
                        uid,
                        "⚠️ <b>Ваша подписка VPN истекла.</b>\n\n"
                        "Для продления нажмите «🛒 Купить VPN».",
                        parse_mode="HTML")
                except Exception:
                    pass

            # Ogohlantirish / Напоминания об истечении (har kun faqat bir marta)
            for days in [3, 1]:
                expiring = await get_expiring_users(days)
                for user_id, username in expiring:
                    sent_days = notified_expiring.setdefault(user_id, set())
                    key = (today, days)
                    if key in sent_days:
                        continue
                    sent_days.add(key)
                    try:
                        await bot.send_message(
                            user_id,
                            f"⏰ <b>Подписка истекает через {days} дн.!</b>\n\n"
                            f"Успейте продлить, нажав «🛒 Купить VPN».",
                            parse_mode="HTML")
                    except Exception:
                        pass

            # Kunlik hisobot / Ежедневный отчёт (каждый день в 09:00)
            if (last_daily_report != today and now.hour >= 9):
                last_daily_report = today
                try:
                    s = await get_stats()
                    await bot.send_message(
                        ADMIN_ID,
                        f"📊 <b>Ежедневный отчёт — {now.strftime('%d.%m.%Y')}</b>\n\n"
                        f"👤 Всего пользователей: <b>{s['total']}</b>\n"
                        f"🆕 Новых сегодня: <b>{s['new_today']}</b>\n"
                        f"✅ Активных подписок: <b>{s['paid']}</b>\n"
                        f"⏳ Ожидают оплаты: <b>{s['pending']}</b>\n"
                        f"💰 Доход за сегодня: <b>{s['income_today']} ₽</b>\n"
                        f"💰 Общий доход: <b>{s['income']} ₽</b>",
                        parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Daily report error: {e}")

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(3600)
