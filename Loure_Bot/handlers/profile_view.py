
import logging
from typing import List, Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaAudio, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import INDUSTRIES, TARGETS
from database.crud import get_profile_by_user_id, get_recommended_profiles
from utils.filters import apply_filters

logger = logging.getLogger(__name__)
view_router = Router()

async def send_simple_profile(message: Message, profile: dict) -> bool:
    try:
        media = profile.get('media', [])
        
        if media:
            media_group = []
            caption = (
                f"👤 <b>{profile['name']}</b>\n"
                f"Отрасль: {INDUSTRIES.get(profile['industry'], {}).get('name', profile['industry'])}\n\n"
                f"📝 <b>Описание:</b>\n{profile['description']}\n\n"
                f"<b>Ищет:</b> {TARGETS.get(profile['target'], profile['target'])}\n"
                f"<b>Код:</b> <code>{profile['code']}</code>"
            )
            for i, (media_type, file_id) in enumerate(media):
                if media_type == 'photo':
                    if i == 0:
                        media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode=ParseMode.HTML))
                    else:
                        media_group.append(InputMediaPhoto(media=file_id))
                elif media_type == 'audio':
                    if i == 0:
                        media_group.append(InputMediaAudio(media=file_id, caption=caption, parse_mode=ParseMode.HTML))
                    else:
                        media_group.append(InputMediaAudio(media=file_id))
            await message.answer_media_group(media_group)
            return True

    except Exception as e:
        logger.error(f"Ошибка отправки медиа: {e}")
    
    try:
        text = (
            f"👤 <b>{profile['name']}</b>\n"
            f"Отрасль: {INDUSTRIES.get(profile['industry'], {}).get('name', profile['industry'])}\n\n"
            f"📝 <b>Описание:</b>\n{profile['description']}\n\n"
            f"🔍 <b>Ищет:</b> {TARGETS.get(profile['target'], profile['target'])}\n"
            f"🆔 <b>Код:</b> <code>{profile['code']}</code>"
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки текста: {e}")
        return False

@view_router.callback_query(F.data == "view_profiles")
async def start_viewing(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        user_id = callback.from_user.id
        user_profile = await get_profile_by_user_id(user_id)
        if not user_profile:
            await callback.message.edit_text(
                "⛔️ У вас нет анкеты!\n\n"
                "Сначала создайте анкету.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать анкету", callback_data='create_profile')]
                ])
            )
            return
        recommended_profiles = await apply_filters(user_profile)
        if not recommended_profiles:
            await callback.message.edit_text(
                "👀 Пока нет подходящих анкет.\n\n"
                "Попробуйте позже или измените критерии поиска.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Редактировать анкету", callback_data='edit_profile')]
                ])
            )
            return
        await state.update_data({
            'recommended_profiles': recommended_profiles,
            'current_index': 0,
            'total_profiles': len(recommended_profiles)
        })
        
        logger.info(f"Начат просмотр для user_id={user_id}, найдено {len(recommended_profiles)} анкет")
        await show_current_profile(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка в start_viewing: {e}", exc_info=True)
        await callback.answer("🚨 Произошла ошибка. Попробуйте позже.", show_alert=True)

@view_router.callback_query(F.data == "next_profile")
async def show_next_profile(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        data = await state.get_data()
        current_index = data.get('current_index', 0)
        profiles = data.get('recommended_profiles', [])
        new_index = current_index + 1
        await state.update_data({'current_index': new_index})
        
        if new_index >= len(profiles):
            await callback.message.edit_text(
                "✅ Вы просмотрели все доступные анкеты!\n\n"
                "Хотите создать свою анкету?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Создать анкету", callback_data='create_profile')],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data='main_menu')]
                ])
            )
            await state.clear()
            return
        await show_current_profile(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка в show_next_profile: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки анкеты", show_alert=True)

async def show_current_profile(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        current_index = data.get('current_index', 0)
        profiles = data.get('recommended_profiles', [])
        total = data.get('total_profiles', 0)
        
        if current_index >= len(profiles):
            await callback.message.answer("✅ Вы просмотрели все анкеты!")
            await state.clear()
            return
        
        current_profile = profiles[current_index]
        await send_simple_profile(callback.message, current_profile)
        keyboard_buttons = []
        
        if current_index + 1 < len(profiles):
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Дальше → ({current_index + 1}/{total})", 
                callback_data='next_profile'
            )])
        else:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Последняя анкета ({current_index + 1}/{total})", 
                callback_data='next_profile'
            )])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="⏹️ Остановить", callback_data='stop_viewing'),
            InlineKeyboardButton(text="🔙 Назад", callback_data='prev_profile')
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.answer(
            f"📄 Анкета {current_index + 1} из {total}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_current_profile: {e}", exc_info=True)
        await callback.answer("❌ Ошибка отображения анкеты", show_alert=True)

@view_router.callback_query(F.data == "prev_profile")
async def show_previous_profile(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        data = await state.get_data()
        current_index = data.get('current_index', 0)
        
        if current_index <= 0:
            await callback.answer("Это первая анкета", show_alert=True)
            return
        new_index = current_index - 1
        await state.update_data({'current_index': new_index})
        await show_current_profile(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка в show_previous_profile: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)

@view_router.callback_query(F.data == "stop_viewing")
async def stop_viewing(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Просмотр остановлен")
    
    await callback.message.edit_text(
        "👌 Просмотр анкет остановлен.\n\n"
        "Что хотите сделать дальше?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать/редактировать анкету", callback_data='create_profile')],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data='main_menu')]
        ])
    )
    await state.clear()

@view_router.message(F.text == "📋 Моя анкета")
@view_router.callback_query(F.data == "my_profile")
async def view_my_profile(message_or_callback: Message | CallbackQuery):
    try:
        user_id = None
        message = None
        
        if isinstance(message_or_callback, CallbackQuery):
            user_id = message_or_callback.from_user.id
            message = message_or_callback.message
            await message_or_callback.answer()
        else:
            user_id = message_or_callback.from_user.id
            message = message_or_callback
        
        profile = await get_profile_by_user_id(user_id)
        
        if not profile:
            text = "❌ У вас еще нет созданной анкеты. Используйте /create чтобы создать анкету."
            
            if isinstance(message_or_callback, CallbackQuery):
                await message.edit_text(text)
            else:
                await message.answer(text)
            return
        await send_simple_profile(message, profile)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data='edit_profile')],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data='delete_confirm')],
            [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data='view_profiles')]
        ])
        
        if isinstance(message_or_callback, CallbackQuery):
            await message.answer("Что вы хотите сделать с анкетой?", reply_markup=keyboard)
        else:
            await message.answer("Что вы хотите сделать с анкетой?", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в view_my_profile: {e}", exc_info=True)
        
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        else:
            await message_or_callback.answer(f"❌ Ошибка: {str(e)}")

@view_router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    
    from handlers.common import start
    await start(callback.message)
@view_router.message(F.text == "/my_ancet")
async def cmd_my_ancet(message: Message):
    await view_my_profile(message)