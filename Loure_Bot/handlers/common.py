import logging
from typing import Any, Dict

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from database.crud import delete_profile_by_user_id, get_profile_by_user_id,get_user_active_chat, save_message, close_chat, is_user_banned, get_chat_by_code, get_chat_messages 
from utils.keyboard import get_main_menu_keyboard

logger = logging.getLogger(__name__)
common_router = Router()

@common_router.message(CommandStart())
async def start(message: Message):
    """Обработчик команды /start"""
    try:
        profile = await get_profile_by_user_id(message.from_user.id)
        
        if profile:
            text = (
                "👋 С возвращением!\n\n"
                "У вас уже есть созданная анкета.\n\n"
                "📋 <b>Доступные действия:</b>\n"
                "• Просмотреть свою анкету\n"
                "• Редактировать анкету\n"
                "• Удалить анкету\n"
                "• Искать другие анкеты"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Моя анкета", callback_data="my_profile")],
                [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
                [InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_confirm")],
                [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data="view_profiles")]
            ])
        else:
            text = (
                "👋 Привет! Я бот для творческих знакомств.\n\n"
                "Здесь вы можете:\n"
                "✅ Создать свою анкету\n"
                "✅ Найти единомышленников\n"
                "✅ Найти клиентов или исполнителей\n\n"
                "Начните с создания анкеты!"
            )
            
            keyboard = get_main_menu_keyboard()
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        )

@common_router.message(Command("cancel"))
@common_router.callback_query(F.data == "cancel")
async def cancel(message_or_callback: Message | CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("Действие отменено")
            await message_or_callback.message.edit_text(
                "Действие отменено.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message_or_callback.answer(
                "Действие отменено.",
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в cancel: {e}", exc_info=True)
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("Ошибка при отмене")


@common_router.message(Command("delete"))
async def delete_profile_user(message: Message):
    from database.crud import delete_profile_by_user_id, get_profile_by_user_id
    
    profile = await get_profile_by_user_id(message.from_user.id)
    
    if not profile:
        await message.answer("❌ У вас нет активной анкеты для удаления.")
        return
    
    await message.answer(
        f"⚠️ Вы уверены, что хотите удалить свою анкету?\n\n"
        f"Имя: {profile['name']}\n"
        f"Отрасль: {profile['industry']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"user_delete_confirm_{profile['code']}"),
                InlineKeyboardButton(text="❌ Нет, отмена", callback_data="user_delete_cancel")
            ]
        ])
    )

@common_router.callback_query(F.data.startswith("user_delete_confirm_"))
async def confirm_user_delete(callback: CallbackQuery, bot: Bot):
    code = callback.data.split("_")[-1]
    
    from database.crud import delete_profile_by_code, get_profile_by_user_id
    
    profile = await get_profile_by_user_id(callback.from_user.id)
    if not profile or profile['code'] != code:
        await callback.answer("❌ Вы не можете удалить эту анкету!", show_alert=True)
        return
    
    success = await delete_profile_by_code(code)
    
    if success:
        await callback.message.edit_text("✅ Ваша анкета успешно удалена!")
        from config import ADMIN_CHAT_ID
        if ADMIN_CHAT_ID:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"👤 Пользователь @{callback.from_user.username or callback.from_user.id} "
                f"удалил свою анкету:\n"
                f"Код: {code}\n"
                f"Имя: {profile['name']}"
            )
    else:
        await callback.message.edit_text("❌ Не удалось удалить анкету.")
    
    await callback.answer()

@common_router.callback_query(F.data == "user_delete_cancel")
async def cancel_user_delete(callback: CallbackQuery):
    await callback.message.edit_text("✅ Удаление анкеты отменено.")
    await callback.answer()

@common_router.message(F.text & ~F.command)
async def handle_text(message: Message, state: FSMContext):
    """Обработка текстовых сообщений вне состояний"""
    try:
        current_state = await state.get_state()
        
        if current_state:
            return
        profile = await get_profile_by_user_id(message.from_user.id)
        
        if profile:
            text = (
                "📋 <b>Доступные действия:</b>\n\n"
                "2. /my_ancet - Моя анкета\n"
                "3. /edit - Редактировать анкету\n"
                "4. /delete - Удалить анкету\n"
                "5. /ban_info - Правила\n\n"
                "Или используйте кнопки ниже:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Моя анкета", callback_data="my_profile")],
                [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
                [InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_confirm")],
                [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data="view_profiles")],
                [InlineKeyboardButton(text="❗️ Правила", callback_data="ban_info")]

])
        else:
            text = (
                "👋 <b>Привет!</b>\n\n"
                "У вас еще нет анкеты.\n"
                "Создайте её, чтобы начать пользоваться ботом!\n\n"
                "Доступные команды:\n"
                "/start - Главное меню\n"
                "/create - Создать анкету\n"
                "/cancel - Отменить действие"
            )
            
            keyboard = get_main_menu_keyboard()
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_text: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

async def error_handler(event: Any, exception: Exception):
    try:
        logger.error(f"Необработанное исключение: {exception}", exc_info=True)
        if isinstance(event, Message):
            await event.answer(
                "❌ Произошла непредвиденная ошибка.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "❌ Произошла ошибка. Попробуйте еще раз.",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике ошибок: {e}", exc_info=True)


@common_router.message(F.text & ~F.command)
async def handle_chat_message(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if await is_user_banned(user_id):
        await message.answer("❌ Вы забанены и не можете отправлять сообщения.")
        return
    chat = await get_user_active_chat(user_id)
    
    if not chat:
        return
    
    if user_id == chat['customer_id']:
        receiver_id = chat['executor_id']
        role = "Заказчик"
    else:
        receiver_id = chat['customer_id']
        role = "Исполнитель"
    
    await save_message(
        chat_code=chat['chat_code'],
        sender_id=user_id,
        receiver_id=receiver_id,
        message_text=message.text,
        message_type='text'
    )
    await message.bot.send_message(
        chat_id=receiver_id,
        text=f"<b>{role}:</b>\n{message.text}",
        parse_mode=ParseMode.HTML
    )
    await message.answer("✅ Сообщение доставлено собеседнику анонимно.")


@common_router.message(Command("close_chat"))
async def close_chat_command(message: Message):
    user_id = message.from_user.id
    chat = await get_user_active_chat(user_id)
    
    if not chat:
        await message.answer("❌ У вас нет активного чата.")
        return
    
    await close_chat(chat['chat_code'])
    await message.answer(f"✅ Чат закрыт. Сообщения больше не будут доставляться.")


@common_router.message(Command("complaint"))
async def complaint_command(message: Message):
    user_id = message.from_user.id
    chat = await get_user_active_chat(user_id)
    
    if not chat:
        await message.answer("❌ У вас нет активного чата.")
        return
    
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Не указана"
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO complaints (user_id, chat_code, reason) VALUES (?, ?, ?)",
            (user_id, chat['chat_code'], reason)
        )
        await db.commit()
    if ADMIN_CHAT_ID:
        await message.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⚠️ <b>НОВАЯ ЖАЛОБА!</b>\n\n"
                 f"Чат: {chat['chat_code']}\n"
                 f"Пользователь: {user_id}\n"
                 f"Причина: {reason}",
            parse_mode=ParseMode.HTML
        )
    
    await message.answer("✅ Жалоба отправлена администратору.")
