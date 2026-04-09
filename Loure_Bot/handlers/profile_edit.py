
import json
import logging
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from config import INDUSTRIES, TARGETS
from utils.keyboard import get_target_keyboard
from database.crud import get_profile_by_user_id, save_profile_crud
from .profile_creanion import send_full_profile 

logger = logging.getLogger(__name__)
edit_router = Router()

@edit_router.message(Command("edit"))
@edit_router.callback_query(F.data == "edit_profile")
async def start_edit_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    current_profile = await get_profile_by_user_id(callback.from_user.id)
    
    if not current_profile:
        await callback.message.answer("У вас нет анкеты для редактирования. Создайте новую командой /start")
        return
    await state.update_data(
        current=current_profile,
        original_code=current_profile['code']
    )
    industry = current_profile['industry']
    
    if industry in ['artist', 'writer']:
        media_count = len(current_profile.get('media', []))
        await callback.message.answer(
            f"Текущие фото: {media_count} шт.\n\n"
            f"Отправьте новые фото (до {INDUSTRIES[industry]['max_files']} шт) или нажмите 'Оставить'",
            reply_markup=get_skip_keyboard()
        )
    elif industry == 'musician':
        media_count = len(current_profile.get('media', []))
        await callback.message.answer(
            f"Текущие аудио: {media_count} шт.\n\n"
            f"Отправьте новые аудио (до {INDUSTRIES[industry]['max_files']} шт, MP3) или нажмите 'Оставить'",
            reply_markup=get_skip_keyboard()
        )
    
    await state.set_state(ProfileEditing.edit_photos)
    
class ProfileEditing(StatesGroup):
    edit_photos = State()      
    edit_name = State()        
    edit_description = State()
    edit_target = State()      
    finish = State()     

def get_skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оставить как было", callback_data="skip_step")]
    ])

def get_target_keyboard_with_skip():
    buttons = []
    for key, value in TARGETS.items():
        buttons.append([InlineKeyboardButton(text=value, callback_data=f"target_{key}")])
    buttons.append([InlineKeyboardButton(text="Оставить как было", callback_data="skip_step")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@edit_router.callback_query(F.data == "skip_step", ProfileEditing.edit_photos)
async def skip_photos(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    current = data.get('current', {})
    await state.update_data(edited_media=current.get('media', []))
    await ask_edit_name(callback.message, state, current.get('name', ''))


@edit_router.message(F.photo | F.video, ProfileEditing.edit_photos)
async def edit_photo(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        current = data.get('current', {})
        industry = current.get('industry')
        max_files = INDUSTRIES[industry]['max_files']
        
        new_media = data.get('new_media', [])
        
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            file_id = message.video.file_id
            media_type = 'video'
        else:
            return
        
        new_media.append((media_type, file_id))
        await state.update_data(new_media=new_media)
        
        if len(new_media) >= max_files:
            if len(new_media) > max_files:
                new_media = new_media[:max_files]
                await state.update_data(new_media=new_media)
                await message.answer(f"⚠️ Удалено лишнее (максимум {max_files})")
            
            await state.update_data(edited_media=new_media)
            await ask_edit_name(message, state, current.get('name', ''))
        else:
            remaining = max_files - len(new_media)
            
    except Exception as e:
        logger.error(f"Ошибка редактирования медиа: {e}")
        await message.answer("⚠️ Ошибка. Отправьте фото или видео снова.")


@edit_router.message(F.video, ProfileEditing.edit_photos)
async def edit_audio(message: Message, state: FSMContext):
    try:
        if message.audio.mime_type != 'video':
            await message.answer("видео")
            return
        
        data = await state.get_data()
        current = data.get('current', {})
        max_audio = INDUSTRIES[current['industry']]['max_files']
        new_media = data.get('new_media', [])
        new_media.append(('video', message.video.file_id))
        await state.update_data(new_media=new_media)
        
        if len(new_media) >= max_audio:
            if len(new_media) > max_audio:
                new_media = new_media[:max_audio]
                await state.update_data(new_media=new_media)
                await message.answer(f"⚠️ Удалено лишнее видио")
            
            await state.update_data(edited_media=new_media)
            await ask_edit_name(message, state, current.get('name', ''))
        else:
            remaining = max_audio - len(new_media)
            
    except Exception as e:
        logger.error(f"Ошибка редактирования аудио: {e}")
        await message.answer("⚠️ Ошибка. Отправьте аудио снова.")

async def ask_edit_name(message: Message, state: FSMContext, current_name: str):
    await message.answer(
        f"Текущее имя: {current_name}\n\n"
        "Отправьте новое имя или нажмите 'Оставить'",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ProfileEditing.edit_name)


@edit_router.callback_query(F.data == "skip_step", ProfileEditing.edit_name)
async def skip_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    current = data.get('current', {})
    await state.update_data(edited_name=current.get('name', ''))
    await ask_edit_description(callback.message, state, current.get('description', ''))


@edit_router.message(ProfileEditing.edit_name)
async def edit_name(message: Message, state: FSMContext):
    await state.update_data(edited_name=message.text)
    data = await state.get_data()
    current = data.get('current', {})
    await ask_edit_description(message, state, current.get('description', ''))

async def ask_edit_description(message: Message, state: FSMContext, current_description: str):
    preview = current_description[:100] + "..." if len(current_description) > 100 else current_description
    await message.answer(
        f"Текущее описание:\n{preview}\n\n"
        "Отправьте новое описание или нажмите 'Оставить'",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ProfileEditing.edit_description)


@edit_router.callback_query(F.data == "skip_step", ProfileEditing.edit_description)
async def skip_description(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    current = data.get('current', {})
    await state.update_data(edited_description=current.get('description', ''))
    await ask_edit_target(callback.message, state, current.get('target', ''))


@edit_router.message(ProfileEditing.edit_description)
async def edit_description(message: Message, state: FSMContext):
    await state.update_data(edited_description=message.text)
    data = await state.get_data()
    current = data.get('current', {})
    await ask_edit_target(message, state, current.get('target', ''))

async def ask_edit_target(message: Message, state: FSMContext, current_target: str):
    target_name = TARGETS.get(current_target, current_target)
    await message.answer(
        f"Текущая цель: {target_name}\n\n"
        "Выберите новую цель или нажмите 'Оставить'",
        reply_markup=get_target_keyboard_with_skip()
    )
    await state.set_state(ProfileEditing.edit_target)


@edit_router.callback_query(F.data.startswith("target_"), ProfileEditing.edit_target)
async def edit_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    target = callback.data.split('_')[1]
    await state.update_data(edited_target=target)
    await finish_edit_profile(callback.message, state)


@edit_router.callback_query(F.data == "skip_step", ProfileEditing.edit_target)
async def skip_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    current = data.get('current', {})
    await state.update_data(edited_target=current.get('target', ''))
    await finish_edit_profile(callback.message, state)

async def finish_edit_profile(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        current = data.get('current', {})
        
        # Собираем финальную анкету
        edited_profile = {
            'user_id': current['user_id'],
            'username': current.get('username'),
            'name': data.get('edited_name', current.get('name')),
            'industry': current.get('industry'),
            'description': data.get('edited_description', current.get('description')),
            'target': data.get('edited_target', current.get('target')),
            'media': data.get('edited_media', current.get('media', [])),
            'code': data.get('original_code'),  # сохраняем старый код
            'created_at': current.get('created_at', datetime.now().isoformat())
        }
        success = await save_profile_crud(edited_profile)
        
        if not success:
            raise Exception("Не удалось сохранить обновлённую анкету")
        
        await send_full_profile(message, edited_profile)
        
        await state.clear()
        await message.answer(
            "✅ Анкета успешно обновлена! Хотите просмотреть другие анкеты?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Смотреть анкеты", callback_data='view_profiles')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка сохранения отредактированной анкеты: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка при сохранении изменений. "
            "Попробуйте начать заново командой /start"
        )
        await state.clear()
