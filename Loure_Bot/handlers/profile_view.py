
import logging
import re
import aiosqlite
from typing import List, Dict, Optional
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import INDUSTRIES, TARGETS, ADMIN_CHAT_ID, DB_PATH
from database.crud import get_profile_by_user_id, get_recommended_profiles, get_visit_count,increment_daily_visit, increment_visit_count,save_response, check_response, get_responses_count, get_active_chat_by_users,get_user_active_chat,save_message, close_chat, is_user_banned,get_profile_by_code,get_reactions,save_reaction
from utils.filters import apply_filters

logger = logging.getLogger(__name__)
view_router = Router()

def extract_channel_link(text: str) -> str | None:
    if not text:
        return None
    text_lower = text.lower()
    
    url_match = re.search(r'https?://t\.me/([a-zA-Z0-9_]+)', text_lower)
    if url_match:
        return f"https://t.me/{url_match.group(1)}"
    social_patterns = [
        r'тт\s*:\s*@',      # тт: @username
        r'твитер\s*:\s*@',  # твитер: @username
        r'twitter\s*:\s*@', # twitter: @username
        r'instagram\s*:\s*@', # instagram: @username
        r'инстаграм\s*:\s*@', # инстаграм: @username
    ]
    for pattern in social_patterns:
        if re.search(pattern, text_lower):
            continue
    at_match = re.search(r'(?<![a-zA-Z0-9/])@([a-zA-Z0-9_]{5,32})\b', text)
    if at_match:
        return f"https://t.me/{at_match.group(1)}"
    return None
    
async def send_simple_profile(message: Message, profile: dict) -> bool:
    try:
        media = profile.get('media', [])
        
        if media:
            media_group = []
            caption = (
                f"👤 <b>{profile['name']}</b>\n"
                f"📝 <b>Описание:</b>\n{profile['description']}\n\n"
                f"<b>Код:</b> <code>{profile['code']}</code>"
            )
            for i, (media_type, file_id) in enumerate(media):
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
                        await message.answer_audio(media.media, caption=media.caption, parse_mode=media.parse_mode)
                else:
                    await message.answer_media_group(media_group)
                media_sent = True

        if media_sent:
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
                "Пока нет подходящих анкет.\n\n"
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
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

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

        target = current_profile.get('target','')
        
        keyboard_buttons = []
        reaction_buttons = []

        reactions = await get_reactions(current_profile['code'])
        
        for emoji, callback_name in [("❤️", "like"), ("✨", "fire"), ("💫", "art")]:
            count = reactions.get(emoji, 0)
            text = f"{emoji} {count}" if count > 0 else emoji
            reaction_buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=f"react_{current_profile['code']}_{callback_name}"
            ))
        
        if reaction_buttons:
            keyboard_buttons.append(reaction_buttons)
    
        if target == 'executor':
            responses_count = await get_responses_count(current_profile['code'])
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Откликнуться({responses_count})",
                callback_data=f"respond_{current_profile['code']}"
            )])
        elif target == 'customer':
            keyboard_buttons.append([InlineKeyboardButton(
                text="Отзывы",
                callback_data=f"view_reviews_{current_profile['code']}"
            )])
        else:
            channel_link = extract_channel_link(current_profile.get('description', ''))
            if channel_link:
                visit_count = await get_visit_count(current_profile['code']) if channel_link else 0
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"На канал({visit_count})",
                    callback_data=f"visit_channel_{current_profile['code']}"
                )])
                
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
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.answer(
            "__________________________",
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
            [InlineKeyboardButton(text="Создать/редактировать анкету", callback_data='create_profile')],
            [InlineKeyboardButton(text="Главное меню", callback_data='main_menu')]
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


@view_router.callback_query(F.data.startswith("visit_channel_"))
async def handle_visit_channel(callback: CallbackQuery):
    try:
        code = callback.data.split("_")[-1]
        profile = await get_profile_by_user_id(callback.from_user.id)
        from database.crud import get_profile_by_code
        target_profile = await get_profile_by_code(code)

        if not target_profile:
            await callback.answer("❌ Анкета не найдена", show_alert=True)
            return

        channel_link = extract_channel_link(target_profile.get('description', ''))

        if not channel_link:
            await callback.answer("❌ Ссылка на канал не найдена в этой анкете", show_alert=True)
            return
        await increment_visit_count(code)  
        await increment_daily_visit(code, target_profile['user_id']) 

        new_count = await get_visit_count(code)

        await callback.answer("🔓 Открываю канал...")
        try:
            pass
        except Exception:
            pass 

        await callback.message.answer(
            f"🔗 <b>Ссылка на канал пользователя {target_profile['name']}:</b>\n{channel_link}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False  # Telegram покажет превью ссылки
        )

        await callback.message.answer(
            f"✅ Спасибо за интерес! У канала теперь {new_count} переходов."
        )

    except Exception as e:
        logger.error(f"Ошибка в handle_visit_channel: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

async def send_profile_to_user(bot: Bot, user_id: int, profile: dict):
    try:
        media = profile.get('media', [])
        
        caption = (
            f"👤 <b>{profile['name']}</b>\n"
            f"Отрасль: {INDUSTRIES.get(profile['industry'], {}).get('name', profile['industry'])}\n\n"
            f"📝 <b>Описание:</b>\n{profile['description']}\n\n"
            f"<b>Ищет:</b> {TARGETS.get(profile['target'], profile['target'])}\n"
            f"<b>Код:</b> <code>{profile['code']}</code>\n\n"
            f"<i>✨ Этот пользователь откликнулся на вашу анкету!</i>"
        )
        
        if media:
            media_group = []
            for i, (media_type, file_id) in enumerate(media):
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
                await bot.send_media_group(chat_id=user_id, media=media_group)
        else:
            await bot.send_message(chat_id=user_id, text=caption, parse_mode=ParseMode.HTML)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_response_{profile['code']}"),
                InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_response_{profile['code']}")
            ]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text="📌 Что делаем с этим откликом?",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки анкеты пользователю {user_id}: {e}")


@view_router.callback_query(F.data.startswith("respond_"))
async def handle_response(callback: CallbackQuery, bot: Bot):
    try:
        code = callback.data.split("_")[-1]
        customer_profile = await get_profile_by_code(code)
        if not customer_profile:
            await callback.answer("❌ Анкета не найдена", show_alert=True)
            return
        if await is_user_banned(callback.from_user.id):
            await callback.answer("❌ Вы забанены и не можете использовать эту функцию", show_alert=True)
            return
        executor_profile = await get_profile_by_user_id(callback.from_user.id)
        if not executor_profile:
            await callback.answer("❌ У вас нет анкеты. Создайте её!", show_alert=True)
            return
        if await check_response(customer_profile['code'], callback.from_user.id):
            await callback.answer("✅ Вы уже откликались на эту анкету", show_alert=True)
            return
        await save_response(customer_profile['code'], callback.from_user.id, executor_profile['name'])
        await send_profile_to_user(
            bot=bot,
            user_id=customer_profile['user_id'],
            profile=executor_profile,
        )
        
        await callback.answer("✅ Ваша анкета отправлена заказчику!")
        await callback.message.answer(
            "✅ Вы откликнулись на анкету!\n"
            "Заказчик получил вашу анкету и свяжется с вами, если вы заинтересовали."
        )
        
        logger.info(f"Отклик от {callback.from_user.id} на анкету {code}")
        
    except Exception as e:
        logger.error(f"Ошибка отклика: {e}")
        await callback.answer("❌ Ошибка при отправке отклика", show_alert=True)



@view_router.callback_query(F.data.startswith("accept_response"))
async def accept_response(callback: CallbackQuery, bot: Bot):
    try:
        executor_code = callback.data.split("_")[-1]
        executor_profile = await get_profile_by_code(executor_code)
        customer_profile = await get_profile_by_user_id(callback.from_user.id)
        
        if not customer_profile or not executor_profile:
            await callback.answer("❌ Анкета не найдена", show_alert=True)
            return
        
        customer_code = customer_profile['code']
        existing_chat = await get_active_chat_by_users(customer_profile['user_id'], executor_profile['user_id'])
        
        if existing_chat:
            chat_code = existing_chat['chat_code']
            await callback.message.edit_text(
                f"✅ Чат уже существует!\n"
                f"Код чата: <code>{chat_code}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            chat_code = f"{customer_code}_{executor_code}"
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO chats 
                       (chat_code, customer_id, executor_id, customer_profile_code, executor_profile_code, status, created_at) 
                       VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                    (chat_code, customer_profile['user_id'], executor_profile['user_id'], 
                     customer_code, executor_code, datetime.now().isoformat())
                )
                await db.commit()
            
            for user_id, role in [(customer_profile['user_id'], 'Заказчик'), (executor_profile['user_id'], 'Исполнитель')]:
                other_code = executor_code if role == 'Заказчик' else customer_code
                
                await bot.send_message(
                    chat_id=user_id,
                    text=f"🆕 <b>Создан анонимный чат!</b>\n\n"
                         f"Ваша роль: {role}\n"
                         f"Код чата: <code>{chat_code}</code>\n\n"
                         f"<b>Как это работает:</b>\n"
                         f"• Отправляйте сообщения:\n<code>/send {other_code} Ваше сообщение</code>\n\n"
                         f"• Все чаты: /my_chats\n"
                         f"• История: /chat_history {other_code}\n"
                         f"• Закрыть чат: /close_chat {other_code}\n"
                         f"• Пожаловаться: /complaint {other_code} причина",
                    parse_mode=ParseMode.HTML
                )
            
            await callback.message.edit_text(
                f"✅ Отклик принят! Чат создан.\n"
                f"Код чата: <code>{chat_code}</code>",
                parse_mode=ParseMode.HTML
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка принятия отклика: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@view_router.callback_query(F.data.startswith("react_"))
async def handle_reaction(callback: CallbackQuery, state: FSMContext):
    try:
        _, profile_code, reaction_type = callback.data.split("_")
        
        emoji_map = {"like": "❤️", "fire": "✨", "art": "💫"}
        emoji = emoji_map.get(reaction_type, "❤️")
        
        await save_reaction(profile_code, callback.from_user.id, emoji)
        
        data = await state.get_data()
        current_index = data.get('current_index', 0)
        profiles = data.get('recommended_profiles', [])
        total = data.get('total_profiles', 0)
        
        if current_index >= len(profiles):
            return
        
        current_profile = profiles[current_index]
        
        target = current_profile.get('target', '')
        keyboard_buttons = []
        
        reactions = await get_reactions(profile_code)
        reaction_buttons = []
        for emoji_btn, cb_name in [("❤️", "like"), ("✨", "fire"), ("💫", "art")]:
            count = reactions.get(emoji_btn, 0)
            text = f"{emoji_btn} {count}" if count > 0 else emoji_btn
            reaction_buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=f"react_{profile_code}_{cb_name}"
            ))
        if reaction_buttons:
            keyboard_buttons.append(reaction_buttons)
        
        if target == 'executor':
            responses_count = await get_responses_count(profile_code)
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"Откликнуться ({responses_count})",
                callback_data=f"respond_{profile_code}"
            )])
        else:
            channel_link = extract_channel_link(current_profile.get('description', ''))
            if channel_link:
                visit_count = await get_visit_count(profile_code)
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"На канал ({visit_count})",
                    callback_data=f"visit_channel_{profile_code}"
                )])
        
        nav_buttons = []
        if current_index + 1 < total:
            nav_buttons.append(InlineKeyboardButton(text=f"Дальше → ({current_index + 1}/{total})", callback_data="next_profile"))
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка реакции: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
