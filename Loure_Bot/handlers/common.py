import logging
from typing import Any, Dict

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from database.crud import delete_profile_by_user_id, get_profile_by_user_id,get_user_active_chat, save_message, close_chat, is_user_banned, get_chat_by_codes, get_chat_messages,get_or_create_chat,get_profile_by_code
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

async def get_chat_by_codes(code1: str, code2: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM chats 
               WHERE (customer_profile_code = ? AND executor_profile_code = ?)
               OR (customer_profile_code = ? AND executor_profile_code = ?)""",
            (code1, code2, code2, code1)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_or_create_chat(customer_code: str, executor_code: str) -> dict:
    chat = await get_chat_by_codes(customer_code, executor_code)
    if chat:
        return chat
    
    chat_code = f"{customer_code}_{executor_code}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO chats (chat_code, customer_profile_code, executor_profile_code, status)
               VALUES (?, ?, ?, 'active')""",
            (chat_code, customer_code, executor_code)
        )
        await db.commit()
    
    return await get_chat_by_codes(customer_code, executor_code)


@common_router.message(Command("send"))
async def send_message_to_chat(message: Message):
    user_id = message.from_user.id
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Используйте: /send КОД_АНКЕТЫ ТЕКСТ\n\n"
            "Пример: /send aB3dE5fG Привет!"
        )
        return
    
    target_code = args[1]
    msg_text = args[2]
    sender_profile = await get_profile_by_user_id(user_id)
    if not sender_profile:
        await message.answer("❌ У вас нет анкеты")
        return
    target_profile = await get_profile_by_code(target_code)
    if not target_profile:
        await message.answer(f"❌ Анкета {target_code} не найдена")
        return
    
    # Сохраняем сообщение в БД
    chat_code = f"{sender_profile['code']}_{target_code}"
    
    await save_message(
        chat_code=chat_code,
        sender_id=user_id,
        receiver_id=target_profile['user_id'],
        message_text=msg_text
    )
    
    # Отправляем получателю
    await message.bot.send_message(
        chat_id=target_profile['user_id'],
        text=f"<b>{sender_profile['name']}</b> [<code>{sender_profile['code']}</code>]:\n{msg_text}\n\n"
             f"Ответить: /send {sender_profile['code']} Ваше сообщение",
        parse_mode=ParseMode.HTML
    )
    
    await message.answer(f"✅ Сообщение отправлено {target_profile['name']}")


@common_router.message(Command("my_chats"))
async def my_chats(message: Message):
    user_id = message.from_user.id
    profile = await get_profile_by_user_id(user_id)
    
    if not profile:
        await message.answer("❌ У вас нет анкеты")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM chats 
               WHERE (customer_profile_code = ? OR executor_profile_code = ?) 
               AND status = 'active'""",
            (profile['code'], profile['code'])
        )
        chats = await cursor.fetchall()
    
    if not chats:
        await message.answer("У вас нет активных чатов.\n\nЧтобы начать чат, откликнитесь на анкету или дождитесь отклика на свою.")
        return
    
    text = "<b>Ваши активные чаты:</b>\n\n"
    for chat in chats:
        if chat['customer_profile_code'] == profile['code']:
            other_code = chat['executor_profile_code']
            other_profile = await get_profile_by_code(other_code)
            role = "Вы заказчик"
        else:
            other_code = chat['customer_profile_code']
            other_profile = await get_profile_by_code(other_code)
            role = "Вы исполнитель"
        
        text += f"┌ <b>{other_profile['name']}</b> [<code>{other_code}</code>]\n"
        text += f"└ {role}\n\n"
    
    text += "Чтобы отправить сообщение: /send [код] [текст]"
    
    await message.answer(text, parse_mode=ParseMode.HTML)


@common_router.message(Command("chat_history"))
async def chat_history(message: Message):
    user_id = message.from_user.id
    profile = await get_profile_by_user_id(user_id)
    
    if not profile:
        await message.answer("❌ У вас нет анкеты")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите код анкеты: /chat_history aB3dE5fG")
        return
    
    other_code = args[1]
    chat = await get_chat_by_codes(profile['code'], other_code)
    if not chat:
        await message.answer(f"❌ Чат с анкетой {other_code} не найден")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages WHERE chat_code = ? ORDER BY created_at ASC LIMIT 100",
            (chat['chat_code'],)
        )
        messages = await cursor.fetchall()
    
    if not messages:
        await message.answer(f"Чат с анкетой {other_code} пуст")
        return
    
    other_profile = await get_profile_by_code(other_code)
    
    text = f"<b>История переписки с {other_profile['name']}</b> [<code>{other_code}</code>]\n"
    text += f"{'='*40}\n\n"
    
    for msg in messages:
        if msg['sender_id'] == user_id:
            sender = f"👤 Вы"
        else:
            sender = f"{other_profile['name']}"
        
        text += f"[{msg['created_at'][:16]}] {sender}:\n{msg['message_text']}\n\n"
        
        if len(text) > 3800:
            await message.answer(text, parse_mode=ParseMode.HTML)
            text = ""
    
    if text:
        await message.answer(text, parse_mode=ParseMode.HTML)


@common_router.message(Command("close_chat"))
async def close_chat_command(message: Message):
    user_id = message.from_user.id
    profile = await get_profile_by_user_id(user_id)
    
    if not profile:
        await message.answer("❌ У вас нет анкеты")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите код анкеты: /close_chat aB3dE5fG")
        return
    
    other_code = args[1]
    
    chat = await get_chat_by_codes(profile['code'], other_code)
    if not chat:
        await message.answer(f"❌ Чат с анкетой {other_code} не найден")
        return
    
    await close_chat(chat['chat_code'])
    
    await message.answer(
        f"✅ Чат с анкетой <code>{other_code}</code> закрыт.\n"
        f"Сообщения больше не будут доставляться.",
        parse_mode=ParseMode.HTML
    )


@common_router.message(Command("complaint"))
async def complaint_command(message: Message):
    user_id = message.from_user.id
    profile = await get_profile_by_user_id(user_id)
    
    if not profile:
        await message.answer("❌ У вас нет анкеты")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("❌ Укажите код анкеты: /complaint aB3dE5fG [причина]")
        return
    
    target_code = args[1]
    reason = args[2] if len(args) > 2 else "Не указана"
    target_profile = await get_profile_by_code(target_code)
    if not target_profile:
        await message.answer(f"❌ Анкета с кодом {target_code} не найдена")
        return
    chat = await get_chat_by_codes(profile['code'], target_code)
    if not chat:
        await message.answer(f"❌ У вас нет чата с анкетой {target_code}")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO complaints (user_id, chat_code, reason) VALUES (?, ?, ?)",
            (user_id, chat['chat_code'], reason)
        )
        await db.commit()
    
    from config import ADMIN_CHAT_ID
    if ADMIN_CHAT_ID:
        await message.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⚠️ <b>НОВАЯ ЖАЛОБА!</b>\n\n"
                 f"Чат: {chat['chat_code']}\n"
                 f"От: {user_id}\n"
                 f"На анкету: {target_code}\n"
                 f"Причина: {reason}",
            parse_mode=ParseMode.HTML
        )
    
    await message.answer(f"✅ Жалоба на анкету {target_code} отправлена администратору.")
