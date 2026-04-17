import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from database.crud import (
    get_profile_by_code, 
    get_profile_by_user_id,
    save_review, 
    get_reviews, 
    has_accepted_response
)

logger = logging.getLogger(__name__)
review_router = Router()

class ReviewStates(StatesGroup):
    waiting_for_review = State()


@review_router.callback_query(F.data.startswith("view_reviews_"))
async def view_reviews(callback: CallbackQuery):
    try:
        executor_code = callback.data.split("_")[-1]
        reviews = await get_reviews(executor_code)
        
        executor_profile = await get_profile_by_code(executor_code)
        if not executor_profile:
            await callback.answer("❌ Исполнитель не найден", show_alert=True)
            return
        
        if not reviews:
            text = f"У <b>{executor_profile['name']}</b> пока нет отзывов.\n\nБудьте первым, кто оставит отзыв!"
        else:
            text = f"<b>Отзывы об исполнителе {executor_profile['name']}:</b>\n\n"
            for customer_name, review_text, created_at in reviews:
                text += f"<b>{customer_name}:</b>\n{review_text}\n{created_at[:10]}\n\n"
        
        user_profile = await get_profile_by_user_id(callback.from_user.id)
        can_review = False
        
        if user_profile and user_profile.get('target') == 'executor':
            can_review = await has_accepted_response(callback.from_user.id, executor_code)
        
        keyboard_buttons = []
        if can_review:
            keyboard_buttons.append([InlineKeyboardButton(
                text="Написать отзыв",
                callback_data=f"write_review_{executor_code}"
            )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        
        await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка просмотра отзывов: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@review_router.callback_query(F.data.startswith("write_review_"))
async def write_review_start(callback: CallbackQuery, state: FSMContext):
    executor_code = callback.data.split("_")[-1]
    await state.update_data(executor_code=executor_code)
    await state.set_state(ReviewStates.waiting_for_review)
    await callback.message.answer("Напишите ваш отзыв об исполнителе (текст):")
    await callback.answer()


@review_router.message(ReviewStates.waiting_for_review)
async def save_review_text(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        executor_code = data.get('executor_code')
        
        if not executor_code:
            await message.answer("❌ Ошибка: код исполнителя не найден")
            await state.clear()
            return
        
        user_profile = await get_profile_by_user_id(message.from_user.id)
        if not user_profile:
            await message.answer("❌ У вас нет анкеты")
            await state.clear()
            return
        
        await save_review(executor_code, user_profile['name'], message.text)
        
        await message.answer("✅ Спасибо! Ваш отзыв сохранён и будет виден другим пользователям.")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения отзыва: {e}")
        await message.answer("❌ Ошибка при сохранении отзыва")
        await state.clear()

@review_router.message(Command("my_reviews"))
async def my_reviews(message: Message):
    user_profile = await get_profile_by_user_id(message.from_user.id)
    
    if not user_profile:
        await message.answer("❌ У вас нет анкеты")
        return
    
    if user_profile.get('target') != 'customer':
        await message.answer("❌ Только исполнители могут просматривать отзывы о себе")
        return
    
    reviews = await get_reviews(user_profile['code'])
    
    if not reviews:
        await message.answer("У вас пока нет отзывов")
        return
    
    text = f"<b>Отзывы о вас:</b>\n\n"
    for customer_name, review_text, created_at in reviews:
        text += f"<b>{customer_name}:</b>\n{review_text}\n{created_at[:10]}\n\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)
