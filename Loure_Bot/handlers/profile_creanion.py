import json
import random
import string
import logging
from datetime import datetime
from typing import List, Tuple

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from config import INDUSTRIES, TARGETS, DB_NAME
from utils.keyboard import get_industry_keyboard, get_target_keyboard, get_main_menu_keyboard
from database.crud import save_profile_crud, get_admin_chat, get_profile_by_user_id, can_create_profile
import aiosqlite
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
profile_router = Router()

class ProfileCreation(StatesGroup):
    choose_industry = State()
    get_photos = State()
    get_audio = State()
    get_name = State()
    get_description = State()
    get_target = State()
    finish = State()

async def send_full_profile(message: Message, profile: dict):
    try:
        caption = (
            f"👤 <b>{profile['name']}</b> ({INDUSTRIES[profile['industry']]['name']})\n\n"
            f"📝 <b>Описание:</b>\n{profile['description']}\n"
            f"<b>Ищет:</b> {TARGETS[profile['target']]}\n\n"
            f"<b>Код:</b><code>{profile['code']}</code>"
        )

        media_group = []
        for i, (media_type, file_id) in enumerate(profile['media']):
            if media_type == 'photo':
                if i == 0:
                    media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode=ParseMode.HTML))
                else:
                    media_group.append(InputMediaPhoto(media=file_id))
            elif media_type == 'video':
                if i == 0:
                    media_group.append(InputMediaVideo(media=file_id, caption=caption, parse_mode=ParseMode.HTML))
                else:
                    media_group.append(InputMediaVideo(media=file_id))

        if media_group:
            if len(media_group) == 1:
                media = media_group[0]
                if isinstance(media, InputMediaPhoto):
                    await message.answer_photo(media.media, caption=media.caption, parse_mode=media.parse_mode)
                elif isinstance(media, InputMediaVideo):
                    await message.answer_video(media.media, caption=media.caption, parse_mode=media.parse_mode)
            else:
                await message.answer_media_group(media_group)
        else:
            await message.answer(caption, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Ошибка при отправке анкеты: {e}")
        await message.answer(
            "⚠️ Не удалось отправить анкету с медиа, но вот текстовая версия:\n\n" + caption,
            parse_mode=ParseMode.HTML
        )

async def send_profile_to_admins(bot, profile: dict, admin_chat_id: int):
    try:
        text = (
            f"🆕 Новая анкета:\n\n"
            f"👤 <b>{profile['name']}</b> ({INDUSTRIES[profile['industry']]['name']})\n"
            f"ID: {profile['user_id']}\n"
            f"🔗 Код: <code>{profile['code']}</code>\n\n"
            f"📝 <b>Описание:</b>\n{profile['description']}\n\n"
            f"🔍 <b>Ищет:</b> {TARGETS[profile['target']]}"
        )
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить анкету", callback_data=f"delete_{profile['code']}")]
        ])

        await bot.send_message(
            chat_id=admin_chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        if profile.get('media'):
                media_group = []
                for i, (media_type, file_id) in enumerate(profile['media']):
                    if media_type == 'photo':
                        media = InputMediaPhoto(media=file_id, caption=text if i == 0 else None, parse_mode=ParseMode.HTML)
                    else:
                        media = InputMediaAudio(media=file_id, caption=text if i == 0 else None, parse_mode=ParseMode.HTML)
                    media_group.append(media)
                
                try:
                    await bot.send_media_group(chat_id=admin_chat_id, media=media_group)
                except Exception as media_error:
                    logger.error(f"Ошибка отправки медиа: {media_error}")

    except Exception as e:
        logger.error(f"Ошибка отправки анкеты админам: {e}", exc_info=True)
        raise
@profile_router.callback_query(F.data == "create_profile")
async def start_create_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ProfileCreation.choose_industry)
    
    await callback.message.edit_text(
        text="Выбери свою отрасль:",
        reply_markup=get_industry_keyboard()
    )
    
@profile_router.message(F.data == "create")
async def cmd_create_profile(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileCreation.choose_industry)
    
    await callback.message.edit_text(
        text="Выбери свою отрасль:",
        reply_markup=get_industry_keyboard()
    )
    
@profile_router.callback_query(F.data.startswith("industry_"))
async def choose_industry(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Получен callback: {callback.data}")
        logger.info(f"Текущее состояние: {await state.get_state()}")
        logger.info(f"Ожидаемое состояние: {ProfileCreation.choose_industry}")
        
        current_state = await state.get_state()
        if current_state != ProfileCreation.choose_industry.state:
            logger.warning(f"Неверное состояние: {current_state}")
            await callback.answer("Сначала начните создание анкеты!", show_alert=True)
            return
        
        await callback.answer()
        
        industry = callback.data.split('_')[1]
        logger.info(f"Выбрана отрасль: {industry}")
        await state.update_data(industry=industry)
        
        industry_info = {
            'artist': "Хорошо! Пришли 8 фото/видео примеров работ",
            'writer': "Отлично! Пришли 8 фото/видео примеров работ", 
            'musician': "Супер! пришли 8 клипов с твоей музыкой в видео формате"
        }
        
        await callback.message.edit_text(text=industry_info[industry])
        
        if industry in ['artist', 'writer']:
            await state.set_state(ProfileCreation.get_photos)
            logger.info(f"Переход к состоянию: {ProfileCreation.get_photos}")
        elif industry == 'musician':
            await state.set_state(ProfileCreation.get_audio)
            logger.info(f"Переход к состоянию: {ProfileCreation.get_audio}")
    
    except Exception as e:
        logger.error(f"Ошибка в choose_industry: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка выбора отрасли: {str(e)}")
        await state.clear()

@profile_router.message(F.photo | F.video, ProfileCreation.get_photos)
async def handle_photo(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        media = data.get('media', [])
        
        industry = data.get('industry')
        max_files = INDUSTRIES[industry]['max_files']
        
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            file_id = message.video.file_id
            media_type = 'video'
        else:
            return
        
        media.append((media_type, file_id))
        await state.update_data(media=media)
        
        if len(media) >= max_files:
            if len(media) > max_files:
                media = media[:max_files]
                await state.update_data(media=media)
                await message.answer(f"⚠️ Удалено лишнее (максимум {max_files})")
            await ask_name(message, state)
            
    except Exception as e:
        logger.error(f"Ошибка обработки медиа: {e}")
        await message.answer("⚠️ Ошибка. Отправьте фото или видео снова.")

@profile_router.message(F.video_note, ProfileCreation.get_audio)
async def handle_audio(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        media = data.get('media', [])
        
        industry = data.get('industry')
        max_files = INDUSTRIES[industry]['max_files']
        
        file_id = message.video_note.file_id
        media.append(('video_note', file_id))
        await state.update_data(media=media)
        
        if len(media) >= max_files:
            if len(media) > max_files:
                media = media[:max_files]
                await state.update_data(media=media)
                await message.answer(f"⚠️ Удалено лишнее (максимум {max_files})")
            await ask_name(message, state)
        else:
            remaining = max_files - len(media)
            await message.answer(f"🎬 Пришли еще клип (нужно {max_files}, осталось {remaining})")
            
    except Exception as e:
        logger.error(f"Ошибка обработки клипа: {e}")
        await message.answer("⚠️ Ошибка. Отправьте клип снова.")

async def ask_name(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        media_count = len(data.get('media', []))
        logger.info(f"Переход к имени пользователя. Получено медиа: {media_count}")
        
        await message.answer(
            "Как вас называть? (Это имя будет отображаться в анкете)"
        )
        await state.set_state(ProfileCreation.get_name)
        
    except Exception as e:
        logger.error(f"Ошибка в ask_name: {e}")
        await message.answer("⚠️ Ошибка при обработке")
        await state.clear()

@profile_router.message(ProfileCreation.get_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Опиши чем ты занимаешься, какого рода контент, берешь ли заказы, на каких условиях,"
        "ценник (если есть) и не забудь ссылки на соцсети, сайты и прочие ресурсы где можно "
        "подробнее ознакомиться с твоим творчеством, не забудь юзернейм в Telegram"
    )
    await state.set_state(ProfileCreation.get_description)

@profile_router.message(ProfileCreation.get_description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "Кого ты хочешь найти?",
        reply_markup=get_target_keyboard()
    )
    await state.set_state(ProfileCreation.get_target)

@profile_router.callback_query(F.data.startswith("target_"), ProfileCreation.get_target)
async def get_target(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        target = callback.data.split('_')[1]
        await state.update_data(target=target)
        
        await callback.message.edit_text(
            "Для завершения создания анкеты отправьте любой символ "
            "(например, точку или букву)\n\n"
            "Это подтвердит, что вы готовы сохранить анкету."
        )
        await state.set_state(ProfileCreation.finish)
        
    except Exception as e:
        logger.error(f"Ошибка в get_target: {e}")
        await callback.message.answer("⚠️ Ошибка при обработке выбора")
        await state.clear()

@profile_router.message(ProfileCreation.finish)
async def finish_profile(message: Message, state: FSMContext, bot):
    try:
        if not await can_create_profile(message.from_user.id):
            await message.answer("У вас уже есть 3 анкеты")
            await state.clrar()
            return
            
        data = await state.get_data()
        
        required_fields = ['name', 'industry', 'description', 'target', 'media']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        editing_code = data.get('editing_profile_code')
        if editing_code:
            profile_code = editing_code
            action_text = "обновлена"
        else:
            profile_code = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            action_text = "создана"
        profile = {
            'user_id': message.from_user.id,
            'username': message.from_user.username,
            'name': data['name'],
            'industry': data['industry'],
            'description': data['description'],
            'target': data['target'],
            'media': data.get('media', []),
            'code': profile_code,
            'created_at': datetime.now().isoformat()
        }
        
        success = await save_profile_crud(profile)
        if not success:
            raise Exception("Не удалось сохранить анкету в БД")
        
        await send_full_profile(message, profile)
        admin_chat_id = await get_admin_chat()
        if admin_chat_id:
            await send_profile_to_admins(bot, profile, admin_chat_id)
        await state.clear()
        await message.answer(
            "✅ Анкета успешно создана! Хотите просмотреть другие анкеты?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Смотреть анкеты", callback_data='view_profiles')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка при завершении анкеты: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка при сохранении анкеты. "
            "Попробуйте начать заново командой /start"
        )
        await state.clear()
