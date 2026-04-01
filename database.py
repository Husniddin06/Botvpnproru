import datetime
import aiosqlite
from config import DB, TRIAL_DAYS, REF_BONUS

_lang_cache: dict = {}


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referrer INTEGER,
                balance INTEGER DEFAULT 0,
                trial_start TEXT,
                trial_end TEXT,
                paid INTEGER DEFAULT 0,
                subscription_end TEXT,
                banned INTEGER DEFAULT 0,
                reg_date TEXT,
                language TEXT DEFAULT 'ru'
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tariff TEXT,
                amount INTEGER,
                method TEXT,
                screenshot TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdraws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                wallet TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount INTEGER,
                uses_left INTEGER
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                rating INTEGER,
                comment TEXT,
                created_at TEXT
            )""")
        migrations = [
            ("users",    "subscription_end", "TEXT"),
            ("users",    "banned",           "INTEGER DEFAULT 0"),
            ("users",    "reg_date",         "TEXT"),
            ("users",    "language",         "TEXT DEFAULT 'ru'"),
            ("payments", "created_at",       "TEXT"),
            ("withdraws","created_at",       "TEXT"),
        ]
        for table, col, col_type in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        await db.commit()


async def add_user(user_id: int, username: str, referrer: int = None):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not await cursor.fetchone():
            now = datetime.datetime.now()
            trial_end = now + datetime.timedelta(days=TRIAL_DAYS)
            await db.execute(
                "INSERT INTO users (user_id, username, referrer, trial_start, trial_end, reg_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, referrer, now.isoformat(), trial_end.isoformat(), now.isoformat()))
            await db.commit()
            if referrer:
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id=?",
                    (REF_BONUS, referrer))
                await db.commit()
            return True
    return False


async def get_user(user_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cursor.fetchone()


async def get_all_users():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE banned=0")
        return [row[0] for row in await cursor.fetchall()]


async def get_active_user_ids():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE banned=0 AND paid=1")
        return [row[0] for row in await cursor.fetchall()]


async def get_inactive_user_ids():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE banned=0 AND paid=0")
        return [row[0] for row in await cursor.fetchall()]


async def get_users_count() -> int:
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        return (await cursor.fetchone())[0]


async def get_users_paginated(offset: int, limit: int = 10):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT user_id, username, paid, banned, reg_date FROM users "
            "ORDER BY user_id DESC LIMIT ? OFFSET ?", (limit, offset))
        return await cursor.fetchall()


async def search_user_by_username(username: str):
    clean = username.lstrip("@").lower()
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE LOWER(username)=?", (clean,))
        return await cursor.fetchone()


async def get_user_language(user_id: int) -> str:
    if user_id in _lang_cache:
        return _lang_cache[user_id]
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        lang = row[0] if row and row[0] else 'ru'
    _lang_cache[user_id] = lang
    return lang


async def set_user_language(user_id: int, lang: str):
    _lang_cache[user_id] = lang
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await db.commit()


async def add_payment(user_id: int, tariff: str, amount: int, method: str, screenshot: str = None) -> int:
    async with aiosqlite.connect(DB) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute(
            "INSERT INTO payments (user_id, tariff, amount, method, screenshot, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, tariff, amount, method, screenshot, now))
        await db.commit()
        cursor = await db.execute("SELECT last_insert_rowid()")
        return (await cursor.fetchone())[0]


async def get_pending_payments():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM payments WHERE status='pending' ORDER BY id DESC")
        return await cursor.fetchall()


async def get_payment_by_id(payment_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        return await cursor.fetchone()


async def get_user_payments(user_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
        return await cursor.fetchall()


async def confirm_payment(payment_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payments SET status='confirmed' WHERE id=?", (payment_id,))
        await db.commit()


async def reject_payment(payment_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
        await db.commit()


async def activate_vpn(user_id: int, days: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT subscription_end FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        now = datetime.datetime.now()
        if row and row[0]:
            try:
                current_end = datetime.datetime.fromisoformat(row[0])
                new_end = (current_end + datetime.timedelta(days=days)
                           if current_end > now else now + datetime.timedelta(days=days))
            except Exception:
                new_end = now + datetime.timedelta(days=days)
        else:
            new_end = now + datetime.timedelta(days=days)
        await db.execute(
            "UPDATE users SET paid=1, subscription_end=? WHERE user_id=?",
            (new_end.isoformat(), user_id))
        await db.commit()
    return new_end


async def add_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def deduct_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0


async def create_withdraw(user_id: int, amount: int, wallet: str):
    async with aiosqlite.connect(DB) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute(
            "INSERT INTO withdraws (user_id, amount, wallet, created_at) VALUES (?, ?, ?, ?)",
            (user_id, amount, wallet, now))
        await db.commit()
        cursor = await db.execute("SELECT last_insert_rowid()")
        return (await cursor.fetchone())[0]


async def get_withdraw_by_id(withdraw_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT * FROM withdraws WHERE id=?", (withdraw_id,))
        return await cursor.fetchone()


async def confirm_withdraw(withdraw_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE withdraws SET status='confirmed' WHERE id=?", (withdraw_id,))
        await db.commit()


async def reject_withdraw(withdraw_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE withdraws SET status='rejected' WHERE id=?", (withdraw_id,))
        await db.commit()


async def restore_balance_withdraw(withdraw_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id, amount FROM withdraws WHERE id=?", (withdraw_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id=?", (row[1], row[0]))
            await db.commit()


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def get_promo_code(code: str):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT * FROM promo_codes WHERE code=? AND uses_left > 0", (code.upper(),))
        return await cursor.fetchone()


async def use_promo_code(code: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code=?", (code.upper(),))
        await db.commit()


async def add_promo_code(code: str, discount: int, uses: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO promo_codes (code, discount, uses_left) VALUES (?, ?, ?)",
            (code.upper(), discount, uses))
        await db.commit()


async def save_feedback(user_id: int, rating: int, comment: str = None):
    async with aiosqlite.connect(DB) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO feedback (user_id, rating, comment, created_at) "
            "VALUES (?, ?, ?, ?)", (user_id, rating, comment, now))
        await db.commit()


async def get_feedback_stats() -> dict:
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT AVG(rating), COUNT(*) FROM feedback")
        row = await cursor.fetchone()
        avg = round(row[0], 1) if row[0] else 0
        count = row[1] or 0
    return {"avg": avg, "count": count}


async def has_user_feedback(user_id: int) -> bool:
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT id FROM feedback WHERE user_id=?", (user_id,))
        return bool(await cursor.fetchone())


async def get_referral_leaders(limit: int = 10):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT u.user_id, u.username, COUNT(r.user_id) as cnt "
            "FROM users u JOIN users r ON r.referrer = u.user_id "
            "GROUP BY u.user_id ORDER BY cnt DESC LIMIT ?", (limit,))
        return await cursor.fetchall()


async def get_user_referral_rank(user_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM ("
            "  SELECT referrer, COUNT(*) as cnt FROM users WHERE referrer IS NOT NULL "
            "  GROUP BY referrer HAVING cnt > ("
            "    SELECT COUNT(*) FROM users WHERE referrer=?"
            "  )"
            ")", (user_id,))
        row = await cursor.fetchone()
        rank = (row[0] + 1) if row else 1
        cursor2 = await db.execute("SELECT COUNT(*) FROM users WHERE referrer=?", (user_id,))
        count = (await cursor2.fetchone())[0]
    return rank, count


async def deactivate_expired():
    async with aiosqlite.connect(DB) as db:
        now = datetime.datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE paid=1 AND subscription_end IS NOT NULL "
            "AND subscription_end < ?", (now,))
        expired = [row[0] for row in await cursor.fetchall()]
        if expired:
            await db.execute(
                "UPDATE users SET paid=0 WHERE paid=1 AND subscription_end IS NOT NULL "
                "AND subscription_end < ?", (now,))
            await db.commit()
    return expired


async def get_expiring_users(days: int):
    async with aiosqlite.connect(DB) as db:
        now = datetime.datetime.now()
        start = (now + datetime.timedelta(days=days - 1)).isoformat()
        end   = (now + datetime.timedelta(days=days)).isoformat()
        cursor = await db.execute(
            "SELECT user_id, username FROM users WHERE paid=1 AND subscription_end BETWEEN ? AND ?",
            (start, end))
        return await cursor.fetchall()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB) as db:
        total     = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        paid      = (await (await db.execute("SELECT COUNT(*) FROM users WHERE paid=1")).fetchone())[0]
        banned    = (await (await db.execute("SELECT COUNT(*) FROM users WHERE banned=1")).fetchone())[0]
        pending   = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
        confirmed = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='confirmed'")).fetchone())[0]
        income    = (await (await db.execute(
            "SELECT SUM(amount) FROM payments WHERE status='confirmed'")).fetchone())[0] or 0
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        new_today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))).fetchone())[0]
        month = datetime.datetime.now().strftime('%Y-%m')
        new_month = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{month}%",))).fetchone())[0]
        income_today = (await (await db.execute(
            "SELECT SUM(amount) FROM payments WHERE status='confirmed' AND created_at LIKE ?",
            (f"{today}%",))).fetchone())[0] or 0
    return {
        "total": total, "paid": paid, "banned": banned,
        "pending": pending, "confirmed": confirmed, "income": income,
        "new_today": new_today, "new_month": new_month, "income_today": income_today,
    }
