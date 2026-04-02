import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN 8555630882:AAGqeRiq1jU6W-fqjr_soJTH0168B7Iclsg
from database import init_db
from handlers import user, payment, admin
from handlers.scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.include_router(user.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    await bot.set_my_commands([
        BotCommand(command="start",  description="Главное меню"),
        BotCommand(command="cancel", description="Отменить действие"),
        BotCommand(command="admin",  description="Панель администратора"),
        BotCommand(command="user",   description="Управление пользователем (admin)"),
        BotCommand(command="find",   description="Найти пользователя (admin)"),
        BotCommand(command="users",  description="Список пользователей (admin)"),
        BotCommand(command="backup", description="Резервная копия БД (admin)"),
    ])

    asyncio.create_task(scheduler(bot))
    logger.info("Bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
