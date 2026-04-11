import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.crud import (
    get_weekly_stats, 
    get_filtered_profiles, 
    get_users_with_profiles,
    get_all_profile_codes,
    get_today_visits,
    get_profile_by_code,
    get_profile_by_user_id
)
from config import TOKEN

logger = logging.getLogger(__name__)
bot = Bot(token=TOKEN)


async def send_weekly_notifications():
    try:
        weekly_stats = await get_weekly_stats()
        total_new = weekly_stats.get('total', 0)
        users = await get_users_with_profiles()
        
        logger.info(f"Запуск еженедельной рассылки для {len(users)} пользователей")
        
        for user_id in users:
            try:
                user_profile = await get_profile_by_user_id(user_id)
                
                if not user_profile:
                    continue
                    
                matching_profiles = await get_filtered_profiles(
                    industry=user_profile['industry'],
                    target=user_profile['target'],
                    exclude_user_id=user_id,
                    limit=10
                )
                
                if matching_profiles:
                    message = (
                        f"Привет! Появились новые анкеты!\n\n"
                        f"За неделю создано: {total_new} анкет\n"
                        f"Для вас подходит: {len(matching_profiles)} анкет\n\n"
                        f"Нажми на кнопку ниже, чтобы посмотреть!"
                    )
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Смотреть анкеты", callback_data="view_profiles")]
                        ])
                    )
                    logger.info(f"Отправлена недельная рассылка пользователю {user_id}")
                    await asyncio.sleep(0.5) 
                
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        
        logger.info("Еженедельная рассылка завершена")
        
    except Exception as e:
        logger.error(f"Ошибка в send_weekly_notifications: {e}")


async def send_daily_stats():
    try:
        logger.info("Запуск отправки дневной статистики...")
        
        profiles = await get_all_profile_codes()
        sent_count = 0
        
        for code, user_id in profiles:
            today_visits = await get_today_visits(code)
            
            # Отправляем только если есть переходы
            if today_visits > 0:
                profile = await get_profile_by_code(code)
                if profile:
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"<b>Статистика вашей анкеты за сегодня</b>\n\n"
                                 f"Анкета: {profile.get('name', 'Без имени')}\n"
                                 f"Переходов по ссылке на канал: <b>{today_visits}</b>\n\n"
                                 f"Продолжайте развивать своё творчество!",
                            parse_mode="HTML"
                        )
                        logger.info(f"Отправлена статистика пользователю {user_id}: {today_visits} переходов")
                        sent_count += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Ошибка отправки статистики пользователю {user_id}: {e}")
        
        logger.info(f"Отправка дневной статистики завершена. Отправлено: {sent_count}")
        
    except Exception as e:
        logger.error(f"Ошибка в send_daily_stats: {e}")


async def scheduler():
    logger.info("Планировщик запущен")
    last_weekly_sent = None
    last_daily_sent = None
    
    while True:
        now = datetime.now()
        
        if now.weekday() == 3 and now.hour == 20 and now.minute == 0:
            if last_weekly_sent != now.date():
                logger.info(f"Запуск еженедельной рассылки: {now}")
                await send_weekly_notifications()
                last_weekly_sent = now.date()
                await asyncio.sleep(60)
        
        if now.hour == 20 and now.minute == 0:
            if last_daily_sent != now.date():
                logger.info(f"Запуск дневной статистики: {now}")
                await send_daily_stats()
                last_daily_sent = now.date()
                await asyncio.sleep(60)
        
        await asyncio.sleep(60)
