import asyncio
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers import user, payment, admin
from handlers.scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def health(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Web server started on port 8080")


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

    await start_web_server()
    asyncio.create_task(scheduler(bot))
    logger.info("Bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
