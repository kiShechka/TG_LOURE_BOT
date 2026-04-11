import asyncio
import logging
from database.scheduled import scheduler
from handlers.profile_creanion import profile_router
from handlers.profile_view import view_router
from handlers.common import common_router
from handlers.admin import admin_router
from handlers.info import info_router
from handlers.profile_edit import edit_router

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery


from database.models import init_db
from config import ADMIN_CHAT_ID, TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    from handlers.common import start
    await start(message)

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    from handlers.common import cancel
    await cancel(message, state)

@router.message(Command("my_ancet"))
async def cmd_my_ancet(message: Message):
    from handlers.profile_view import view_my_profile
    await view_my_profile(message)

if ADMIN_CHAT_ID:
    @router.message(Command("delete_admin"), F.chat.id == ADMIN_CHAT_ID)
    async def cmd_delete_admin(message: Message):
        from handlers.admin import delete_profile_command
        await delete_profile_command(message)
    
    @router.message(Command("set_admin_chat"), F.chat.id == ADMIN_CHAT_ID)
    async def cmd_set_admin_chat(message: Message):
        from handlers.admin import set_admin_chat_command
        await set_admin_chat_command(message)
    
    @router.message(Command("info"), F.chat.id == ADMIN_CHAT_ID)
    async def cmd_info(message: Message):
        from handlers.admin import profile_info
        await profile_info(message)

@router.callback_query(F.data == "create_profile")
async def handle_create_profile(callback: CallbackQuery, state: FSMContext):
    from handlers.profile_creanion import start_create_profile
    await start_create_profile(callback, state)
    await callback.answer()

@router.callback_query(F.data == "view_profiles")
async def handle_view_profiles(callback: CallbackQuery, state: FSMContext):
    from handlers.profile_view import start_viewing
    await start_viewing(callback, state)
    await callback.answer()



@router.callback_query(F.data == "next_profile")
async def handle_next_profile(callback: CallbackQuery, state: FSMContext):
    from handlers.profile_view import show_next_profile
    await show_next_profile(callback, state)
    await callback.answer()


if ADMIN_CHAT_ID:
    @router.callback_query(F.data.startswith("delete_"))
    async def handle_admin_delete(callback: CallbackQuery):
        from handlers.admin import delete_profile_callback
        await delete_profile_callback(callback)
        await callback.answer()

        
async def setup_database():
    try:
        loop = asyncio.get_event_loop()
        logger.info("✅ База данных готова")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False

async def main():
    
    storage = MemoryStorage()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)
        
    dp.include_router(router)
    dp.include_router(info_router)
    dp.include_router(profile_router)
    dp.include_router(view_router)
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(edit_router)
    asyncio.create_task(scheduler())
        

    await bot.delete_webhook(drop_pending_updates=True)
        
    logger.info("Бот запущен...")
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())
