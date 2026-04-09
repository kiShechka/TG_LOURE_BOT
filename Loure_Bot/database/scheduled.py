import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.crud import (
    get_weekly_stats, 
    get_filtered_profiles, 
    get_users_with_profiles,
    get_all_profile_codes,
    get_today_visits,
    get_profile_by_code
)
from config import TOKEN

async def send_weekly_notifications():
    bot = Bot(token=TOKEN)
    
    weekly_stats = await get_weekly_stats()
    total_new = weekly_stats.get('total', 0)
    users = await get_users_with_profiles()
    
    for user_id in users:
        try:
            from database.crud import get_profile_by_user_id
            user_profile = await get_profile_by_user_id(user_id)
            
            if not user_profile:
                continue
            matching_profiles = await get_filtered_profiles(
                industry=user_profile['industry'],
                target=user_profile['target'],
                exclude_user_id=user_id
            )
            if matching_profiles:
                message = (
                    f"👋 Привет! Готовы новые анкеты!\n\n"
                    f"📊 За неделю создано: {total_new} анкет\n"
                    f"🎯 Для вас подходит: {len(matching_profiles)} анкет\n\n"
                    f"Чтобы посмотреть анкеты:\n"
                    f"1. Нажмите '🔍 Смотреть анкеты'\n"
                    f"2. Используйте фильтры по своей отрасли\n\n"
                    f"Хороших знакомств! ✨"
                )
                
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data="view_profiles")]
                    ])
                )
            
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
    
    await bot.session.close()

async def scheduler():
    last_weekly_sent = None
    last_daily_sent = None
    
    while True:
        now = datetime.now()
        if now.weekday() == 4 and now.hour == 20 and now.minute == 0:
            if now.weekday() == 4 and now.hour == 20 and now.minute == 0:
                print(f"🕐 Запуск рассылки: {now}")
                await send_weekly_notifications()
                await asyncio.sleep(60)

        if now.hour == 20 and now.minute == 0:
            if now.hour == 20 and now.minute == 0:
            await send_daily_stats()
            # Ждём час, чтобы не отправить несколько раз
            await asyncio.sleep(3600)
            
        await asyncio.sleep(60)
    
async def send_daily_stats():
    logger.info("Запуск отправки дневной статистики...")
    
    profiles = await get_all_profile_codes()
    
    for code, user_id in profiles:
        today_visits = await get_today_visits(code)
        if today_visits > 0:
            profile = await get_profile_by_code(code)
            if profile:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"📊 <b>Статистика вашей анкеты за сегодня</b>\n\n"
                             f"👤 Анкета: {profile.get('name', 'Без имени')}\n"
                             f"🔗 Переходов по ссылке на канал: <b>{today_visits}</b>\n\n"
                             f"Продолжайте развивать своё творчество! 🎨",
                        parse_mode="HTML"
                    )
                    logger.info(f"Отправлена статистика пользователю {user_id}: {today_visits} переходов")
                except Exception as e:
                    logger.error(f"Ошибка отправки статистики пользователю {user_id}: {e}")
    
    logger.info("Отправка дневной статистики завершена")

