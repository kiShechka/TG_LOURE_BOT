
import logging
import asyncio
import aiosqlite
from typing import Optional
from aiogram import Router, F,Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import ADMIN_CHAT_ID, ADMIN_IDS, INDUSTRIES, TARGETS, DB_PATH
from database.crud import (
    delete_profile_by_code, 
    set_admin_chat, 
    get_profile_by_code,
    get_all_profiles,
    get_profile_stats,
    delete_profile_by_user_id,
    get_chat_messages,
    get_chat_by_code,
    ban_user, 
    get_user_active_chat
)
logger = logging.getLogger(__name__)
admin_router = Router()

def is_admin(user_id: int) -> bool:
    if ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID:
        return True
    if ADMIN_IDS and user_id in ADMIN_IDS:
        return True
    return False

async def check_admin(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer(" У вас нет прав администратора.")
        return False
    return True

async def check_admin_callback(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer(" У вас нет прав.", show_alert=True)
        return False
    return True

@admin_router.message(Command("delete_admin"))
async def delete_profile_command(message: Message):
    if not await check_admin(message):
        return
    
    if not message.text or len(message.text.split()) < 2:
        await message.answer(
            "📝 <b>Удаление анкеты</b>\n\n"
            "Использование: <code>/delete_admin &lt;код&gt;</code>\n"
            "или <code>/delete_admin &lt;user_id&gt;</code>\n\n"
            "Пример:\n"
            "<code>/delete_admin ABC123DEF456</code>",
            parse_mode=ParseMode.HTML
        )
        return
    arg = message.text.split()[1]
    
    try:
        user_id = int(arg)
        deleted = await delete_profile_by_user_id(user_id)
        if deleted:
            await message.answer(f"✅ Анкета пользователя {user_id} удалена!")
            logger.info(f"Profile deleted by admin {message.from_user.id}: user_id={user_id}")
            return
        
        deleted = await delete_profile_by_code(arg)
        if deleted:
            await message.answer(f"✅ Анкета с кодом {arg} удалена!")
            logger.info(f"Profile deleted by admin {message.from_user.id}: code={arg}")
        else:
            await message.answer("❌ Анкета не найдена!")
            
    except ValueError:
        deleted = await delete_profile_by_code(arg)
        if deleted:
            await message.answer(f"✅ Анкета с кодом {arg} удалена!")
            logger.info(f"Profile deleted by admin {message.from_user.id}: code={arg}")
        else:
            await message.answer("❌ Анкета не найдена!")
    
    except Exception as e:
        logger.error(f"Ошибка удаления анкеты: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")

@admin_router.message(Command("set_admin_chat"))
async def set_admin_chat_command(message: Message):
    if not await check_admin(message):
        return
    
    try:
        chat_id = message.chat.id
        success = await set_admin_chat(chat_id)
        
        if success:
            await message.answer(
                f"✅ Этот чат установлен как админский!\n\n"
                f"Chat ID: <code>{chat_id}</code>\n"
                f"Название: {message.chat.title or 'Личный чат'}\n\n"
                f"Теперь бот будет отправлять сюда уведомления о новых анкетах.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Admin chat set to {chat_id} by {message.from_user.id}")
        else:
            await message.answer("❌ Не удалось установить админский чат.")
            
    except Exception as e:
        logger.error(f"Ошибка установки админ-чата: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")

@admin_router.message(Command("info"))
async def profile_info(message: Message):
    if not await check_admin(message):
        return
    
    if not message.text or len(message.text.split()) < 2:
        await message.answer(
            "<b>Информация об анкете</b>\n\n"
            "Использование: <code>/info &lt;код&gt;</code>\n"
            "или <code>/info &lt;user_id&gt;</code>\n\n"
            "Пример:\n"
            "<code>/info ABC123DEF456</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    arg = message.text.split()[1]
    
    try:
        profile = None
        try:
            user_id = int(arg)
            from database.crud import get_profile_by_user_id
            profile = await get_profile_by_user_id(user_id)
        except ValueError:
            profile = await get_profile_by_code(arg)
        
        if not profile:
            await message.answer("❌ Анкета не найдена")
            return
        
        from datetime import datetime
        created_at = profile.get('created_at', 'Неизвестно')
        if created_at and not isinstance(created_at, str):
            try:
                created_at = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            except:
                created_at = str(created_at)
        
        text = (
            f"<b>Информация об анкете</b>\n\n"
            f"👤 <b>Имя:</b> {profile.get('name', 'Не указано')}\n"
            f"<b>Username:</b> @{profile.get('username', 'нет')}\n"
            f"<b>User ID:</b> <code>{profile.get('user_id')}</code>\n"
            f"<b>Отрасль:</b> {INDUSTRIES.get(profile.get('industry', ''), {}).get('name', profile.get('industry', 'Неизвестно'))}\n"
            f"<b>Ищет:</b> {TARGETS.get(profile.get('target', ''), profile.get('target', 'Неизвестно'))}\n"
            f"<b>Создана:</b> {created_at}\n"
            f"<b>Код:</b> <code>{profile.get('code', 'Нет кода')}</code>\n\n"
            f"<b>Описание:</b>\n{profile.get('description', 'Нет описания')[:500]}..."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", 
                    callback_data=f"admin_delete_{profile.get('code')}"
                ),
                InlineKeyboardButton(
                    text="Статистика", 
                    callback_data=f"admin_stats_{profile.get('user_id')}"
                )
            ]
        ])
        
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка получения информации об анкете: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")

@admin_router.message(Command("stats"))
async def admin_stats(message: Message):
    if not await check_admin(message):
        return
    try:
        stats = await get_profile_stats()

        if not stats:
            await message.answer("❌ Не удалось получить статистику.")
            return
        
        text = "<b>Статистика бота</b>\n\n"
        
        text += f"<b>Всего анкет:</b> {stats.get('total', 0)}\n\n"
        
        text += "<b>По отраслям:</b>\n"
        for industry_key, industry_data in INDUSTRIES.items():
            count = stats.get(f'industry_{industry_key}', 0)
            text += f"• {industry_data['name']}: {count}\n"
        
        text += "\n<b>По целям:</b>\n"
        for target_key, target_name in TARGETS.items():
            count = stats.get(f'target_{target_key}', 0)
            text += f"• {target_name}: {count}\n"
        
        if stats.get('last_created'):
            text += f"\n🕒 <b>Последняя анкета:</b> {stats['last_created']}"
        
        await message.answer(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")

@admin_router.message(Command("list"))
async def list_profiles(message: Message):
    if not await check_admin(message):
        return
    
    try:
        profiles = await get_all_profiles()
        
        if not profiles:
            await message.answer("Нет созданных анкет.")
            return
        
        text = f"📋 <b>Список анкет ({len(profiles)})</b>\n\n"
        
        for i, profile in enumerate(profiles[:20], 1): 
            text += (
                f"{i}. <b>{profile.get('name', 'Без имени')}</b>\n"
                f"   🆔 <code>{profile.get('code', 'Нет кода')}</code>\n"
                f"   👤 User ID: <code>{profile.get('user_id')}</code>\n"
                f"   🏢 {INDUSTRIES.get(profile.get('industry', ''), {}).get('name', 'Неизвестно')}\n"
                f"   🎯 {TARGETS.get(profile.get('target', ''), 'Неизвестно')}\n\n"
            )
        
        if len(profiles) > 20:
            text += f"\n... и еще {len(profiles) - 20} анкет"
        
        await message.answer(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Ошибка получения списка анкет: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")

@admin_router.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete_callback(callback: CallbackQuery):
    if not await check_admin_callback(callback):
        return
    
    try:
        code = callback.data.split('_')[-1]
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{code}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
            ]
        ])
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить анкету?\n"
            f"Код: <code>{code}</code>\n\n"
            f"Это действие нельзя отменить.",
            parse_mode=ParseMode.HTML,
            reply_markup=confirm_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_delete_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)

@admin_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_callback(callback: CallbackQuery):
    if not await check_admin_callback(callback):
        return
    
    try:
        code = callback.data.split('_')[-1]


        deleted = await delete_profile_by_code(code)
        
        if deleted:
            await callback.message.edit_text(
                f"✅ Анкета <code>{code}</code> успешно удалена!",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Profile {code} deleted via callback by admin {callback.from_user.id}")
        else:
            await callback.message.edit_text("❌ Анкета не найдена или уже удалена.")
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в confirm_delete_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка удаления", show_alert=True)

@admin_router.callback_query(F.data == "cancel_delete")
async def cancel_delete_callback(callback: CallbackQuery):
    await callback.answer("Удаление отменено")
    await callback.message.edit_text("🗑️ Удаление отменено.")

@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_profile_callback(callback: CallbackQuery):
    if not await check_admin_callback(callback):
        return
    
    try:
        code = callback.data.replace('delete_', '', 1)
        
        deleted = await delete_profile_by_code(code)
        
        if deleted:
            await callback.message.edit_text(
                f"✅ Анкета <code>{code}</code> удалена администратором.",
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                f"❌ Не удалось удалить анкету <code>{code}</code>.\n"
                f"Возможно, она уже удалена.",
                parse_mode=ParseMode.HTML
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка удаления анкеты: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при удалении анкеты.")
        await callback.answer()

@admin_router.message(Command("get_chat"))
async def admin_get_chat(message: Message):
    if message.from_user.id != ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите код чата: /get_chat [код]")
        return
    
    chat_code = args[1]
    messages = await get_chat_messages(chat_code, limit=200)
    chat = await get_chat_by_code(chat_code)
    
    if not chat:
        await message.answer(f"❌ Чат {chat_code} не найден")
        return
    
    if not messages:
        await message.answer(f"Чат {chat_code} пуст")
        return
    
    text = f"<b>Переписка чата {chat_code}</b>\n"
    text += f"Заказчик: {chat['customer_id']}\n"
    text += f"Исполнитель: {chat['executor_id']}\n"
    text += f"Статус: {chat['status']}\n"
    text += f"{'='*30}\n\n"
    
    for msg in messages:
        sender = "👤 Заказчик" if msg['sender_id'] == chat['customer_id'] else "🎤 Исполнитель"
        text += f"[{msg['created_at'][:16]}] {sender}:\n{msg['message_text']}\n\n"
        
        if len(text) > 3800:
            await message.answer(text, parse_mode=ParseMode.HTML)
            text = ""
    
    if text:
        await message.answer(text, parse_mode=ParseMode.HTML)


@admin_router.message(Command("ban_user"))
async def admin_ban_user(message: Message):
    if message.from_user.id != ADMIN_IDS:
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите user_id: /ban_user [user_id] [причина]")
        return
    
    try:
        user_id = int(args[0].split()[1] if len(args[0].split()) > 1 else args[0])
    except:
        await message.answer("❌ Неверный формат user_id")
        return
    
    reason = args[1] if len(args) > 1 else "Не указана"
    
    await ban_user(user_id, reason)
    await message.answer(f"✅ Пользователь {user_id} заблокирован\nПричина: {reason}")


@admin_router.message(Command("broadcast"))
async def broadcast_message(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_IDS:
        await message.answer("❌ У вас нет прав для этой команды")
        return
    
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("❌ Укажите текст рассылки после команды /broadcast")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM profiles")
        users = await cursor.fetchall()
    
    status_msg = await message.answer(f"Начинаю рассылку для {len(users)} пользователей...")
    
    success = 0
    fail = 0
    
    for (user_id,) in users:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"Успешно: {success}\n"
        f"❌ Ошибок: {fail}"
    )
