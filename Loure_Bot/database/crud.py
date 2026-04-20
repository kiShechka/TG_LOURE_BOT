
import json
import logging
import secrets
from typing import List, Dict, Optional, Tuple
from datetime import datetime,timedelta,date

import aiosqlite
from config import DB_PATH, DB_TIMEOUT, TARGET_MATCHING, INDUSTRIES, TARGETS
from .models import Profile, dict_to_profile, profile_to_dict

logger = logging.getLogger(__name__)
async def delete_profile_by_user_id(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка удаления анкеты пользователя {user_id}: {e}")
        return False

async def delete_profile_by_code(code: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM profiles WHERE code = ?", (code,))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка удаления анкеты с кодом {code}: {e}")
        return False
    
async def get_connection():
    try:
        conn = await aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT)
        conn.row_factory = aiosqlite.Row  
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД {DB_PATH}: {e}")
        raise

async def save_profile_crud(profile_data: dict) -> bool:
    
    REQUIRED_FIELDS = ['user_id', 'name', 'industry', 'description', 'target', 'code']
    for field in REQUIRED_FIELDS:
        if not profile_data.get(field):
            logger.error(f"Поле {field} обязательно для заполнения")
            raise ValueError(f"Поле {field} обязательно для заполнения")

    if 'media' in profile_data and not isinstance(profile_data['media'], list):
        logger.error("media должен быть списком")
        raise TypeError("media должен быть списком")
    
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute('SELECT 1 FROM profiles WHERE code = ?', (profile_data['code'],)) as cursor:
                exists = await cursor.fetchone()

            if exists:
                await db.execute('''
                UPDATE profiles SET
                    user_id = ?,
                    username = ?,
                    name = ?,
                    industry = ?,
                    description = ?,
                    target = ?,
                    media = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE code = ?
                ''', (
                    profile_data['user_id'],
                    profile_data.get('username'),
                    profile_data['name'],
                    profile_data['industry'],
                    profile_data['description'],
                    profile_data['target'],
                    json.dumps(profile_data.get('media', [])),
                    profile_data['code']
                ))
                logger.info(f"🔄 Анкета обновлена: {profile_data['code']}")
            else:
                await db.execute('''
                INSERT INTO profiles 
                (user_id, username, name, industry, description, target, media, code, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    profile_data['user_id'],
                    profile_data.get('username'),
                    profile_data['name'],
                    profile_data['industry'],
                    profile_data['description'],
                    profile_data['target'],
                    json.dumps(profile_data.get('media', [])),
                    profile_data['code'],
                    profile_data.get('created_at', datetime.now().isoformat())
                ))
                logger.info(f"✅ Анкета создана: {profile_data['code']}")
            
            await db.commit()
            return True
            
    except aiosqlite.IntegrityError as e:
        logger.error(f"❌ Ошибка целостности данных при сохранении анкеты: {e}")
        raise ValueError(f"Ошибка целостности данных: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения анкеты: {e}", exc_info=True)
        raise

async def get_profile_by_user_id(user_id: int) -> Optional[Profile]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Конвертируем Row в dict
                    profile_dict = dict(row)
                    return dict_to_profile(profile_dict)
                return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения анкеты по user_id={user_id}: {e}")
        return None

async def get_profile_by_code(code: str) -> Optional[Profile]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT * FROM profiles WHERE code = ?', (code,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    profile_dict = dict(row)
                    return dict_to_profile(profile_dict)
                return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения анкеты по code={code}: {e}")
        return None

async def get_all_profiles() -> List[Profile]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT * FROM profiles ORDER BY created_at DESC') as cursor:
                rows = await cursor.fetchall()
                profiles = []
                for row in rows:
                    try:
                        profile_dict = dict(row)
                        profiles.append(dict_to_profile(profile_dict))
                    except Exception as e:
                        logger.error(f"Ошибка конвертации строки в профиль: {e}")
                        continue
                return profiles
    except Exception as e:
        logger.error(f"❌ Ошибка получения всех анкет: {e}")
        return []

async def delete_profile_by_user_id(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute('DELETE FROM profiles WHERE user_id = ?', (user_id,)) as cursor:
                await db.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"🗑️ Анкета пользователя {user_id} удалена")
                return deleted
    except Exception as e:
        logger.error(f"❌ Ошибка удаления анкеты user_id={user_id}: {e}")
        return False

async def delete_profile_by_code(code: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute('DELETE FROM profiles WHERE code = ?', (code,)) as cursor:
                await db.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"🗑️ Анкета с кодом {code} удалена")
                return deleted
    except Exception as e:
        logger.error(f"❌ Ошибка удаления анкеты code={code}: {e}")
        return False

async def get_recommended_profiles(user_profile: Profile) -> List[Profile]:
    try:
        target_to_find = TARGET_MATCHING.get(user_profile['target'])
        if not target_to_find:
            logger.warning(f"Неизвестная цель пользователя: {user_profile['target']}")

            return []
        
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            query = '''
            SELECT * FROM profiles 
            WHERE user_id != ? 
            AND target = ?
            ORDER BY created_at DESC
            LIMIT 50
            '''
            
            async with conn.execute(query, (user_profile['user_id'], target_to_find)) as cursor:
                rows = await cursor.fetchall()
                profiles = []
                for row in rows:
                    try:
                        profile_dict = dict(row)
                        profiles.append(dict_to_profile(profile_dict))
                    except Exception as e:
                        logger.error(f"Ошибка конвертации строки в профиль: {e}")
                        continue
                
                logger.info(f"Найдено {len(profiles)} рекомендованных анкет для user_id={user_profile['user_id']}")
                return profiles
                
    except Exception as e:
        logger.error(f"❌ Ошибка получения рекомендаций: {e}", exc_info=True)
        return []

async def get_profiles_by_industry(industry: str) -> List[Profile]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                'SELECT * FROM profiles WHERE industry = ? ORDER BY created_at DESC', 
                (industry,)
            ) as cursor:
                rows = await cursor.fetchall()
                profiles = []
                for row in rows:
                    try:
                        profile_dict = dict(row)
                        profiles.append(dict_to_profile(profile_dict))
                    except Exception as e:
                        logger.error(f"Ошибка конвертации строки в профиль: {e}")
                        continue
                return profiles
    except Exception as e:
        logger.error(f"❌ Ошибка получения анкет по отрасли {industry}: {e}")
        return []

async def get_profiles_by_target(target: str) -> List[Profile]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                'SELECT * FROM profiles WHERE target = ? ORDER BY created_at DESC', 
                (target,)
            ) as cursor:
                rows = await cursor.fetchall()
                profiles = []
                for row in rows:
                    try:
                        profile_dict = dict(row)
                        profiles.append(dict_to_profile(profile_dict))
                    except Exception as e:
                        logger.error(f"Ошибка конвертации строки в профиль: {e}")
                        continue
                return profiles
    except Exception as e:
        logger.error(f"❌ Ошибка получения анкет по цели {target}: {e}")
        return []
async def get_admin_chat() -> Optional[int]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            async with conn.execute('SELECT chat_id FROM admin_chats LIMIT 1') as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.error(f"❌ Ошибка получения админ-чата: {e}")
        return None

async def set_admin_chat(chat_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:

            await db.execute('DELETE FROM admin_chats')  # Удаляем старые
            await db.execute('INSERT INTO admin_chats (chat_id) VALUES (?)', (chat_id,))
            await db.commit()
            logger.info(f"✅ Админ-чат установлен: {chat_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки админ-чата: {e}")
        return False

async def get_profile_stats() -> Dict[str, int]:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as conn:
            stats = {}
            async with conn.execute('SELECT COUNT(*) FROM profiles') as cursor:
                stats['total'] = (await cursor.fetchone())[0]
            for industry in INDUSTRIES:
                async with conn.execute('SELECT COUNT(*) FROM profiles WHERE industry = ?', (industry,)) as cursor:
                    stats[f'industry_{industry}'] = (await cursor.fetchone())[0]
            for target in TARGETS:
                async with conn.execute('SELECT COUNT(*) FROM profiles WHERE target = ?', (target,)) as cursor:
                    stats[f'target_{target}'] = (await cursor.fetchone())[0]
            async with conn.execute('SELECT created_at FROM profiles ORDER BY created_at DESC LIMIT 1') as cursor:
                row = await cursor.fetchone()
                stats['last_created'] = row[0] if row else None
            
            return stats
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return {}
    
async def get_weekly_stats() -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor = await db.execute(
                "SELECT COUNT(*) FROM profiles WHERE created_at >= ?",
                (seven_days_ago,)
            )
            total = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT industry, COUNT(*) FROM profiles WHERE created_at >= ? GROUP BY industry",
                (seven_days_ago,)
            )
            by_industry = {row[0]: row[1] for row in await cursor.fetchall()}
            
            return {
                'total': total,
                'by_industry': by_industry,
                'period': '7 дней'
            }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {'total': 0, 'by_industry': {}, 'period': '7 дней'}

async def get_filtered_profiles(
    industry: str = None, 
    target: str = None,
    exclude_user_id: int = None,
    limit: int = 50
) -> list:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = "SELECT * FROM profiles WHERE 1=1"
            params = []
            
            if industry:
                query += " AND industry = ?"
                params.append(industry)
            
            if target:
                query += " AND target = ?"
                params.append(target)
            
            if exclude_user_id:
                query += " AND user_id != ?"
                params.append(exclude_user_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
    
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
    except Exception as e:
        logger.error(f"Ошибка фильтрации анкет: {e}")
        return []

async def get_users_with_profiles() -> list:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT DISTINCT user_id FROM profiles")
            return [row[0] for row in await cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        return []


async def get_visit_count(code: str) -> int:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute(
                "SELECT visit_count FROM profiles WHERE code = ?", (code,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else 0
    except Exception as e:
        logger.error(f"Ошибка получения счётчика: {e}")
        return 0


async def increment_visit_count(code: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "UPDATE profiles SET visit_count = visit_count + 1 WHERE code = ?",
                (code,)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка увеличения счётчика: {e}")
        return False


async def increment_daily_visit(code: str, user_id: int) -> bool:
    today = datetime.now().date().isoformat()
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute('''
                INSERT INTO daily_stats (code, user_id, date, visits)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(code, date) DO UPDATE SET
                    visits = visits + 1
            ''', (code, user_id, today))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления дневной статистики: {e}")
        return False


async def get_today_visits(code: str) -> int:
    today = datetime.now().date().isoformat()
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute(
                "SELECT visits FROM daily_stats WHERE code = ? AND date = ?",
                (code, today)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка получения дневной статистики: {e}")
        return 0


async def get_all_profile_codes() -> list:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            async with db.execute("SELECT code, user_id FROM profiles") as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения списка анкет: {e}")
        return []


async def save_response(profile_code: str, responder_id: int, responder_name: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "INSERT OR REPLACE INTO responses (profile_code, responder_id, responder_name, created_at) VALUES (?, ?, ?, ?)",
                (profile_code, responder_id, responder_name, datetime.now().isoformat())
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения отклика: {e}")
        return False

async def check_response(profile_code: str, responder_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute(
                "SELECT 1 FROM responses WHERE profile_code = ? AND responder_id = ?",
                (profile_code, responder_id)
            )
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка проверки отклика: {e}")
        return False

async def get_responses_count(profile_code: str) -> int:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM responses WHERE profile_code = ?",
                (profile_code,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка подсчёта откликов: {e}")
        return 0



async def create_anonymous_chat(customer_id: int, executor_id: int, customer_profile_code: str, executor_profile_code: str) -> str:
    chat_code = secrets.token_hex(8)
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                """INSERT INTO chats 
                   (chat_code, customer_id, executor_id, customer_profile_code, executor_profile_code) 
                   VALUES (?, ?, ?, ?, ?)""",
                (chat_code, customer_id, executor_id, customer_profile_code, executor_profile_code)
            )
            await db.commit()
        return chat_code
    except Exception as e:
        logger.error(f"Ошибка создания чата: {e}")
        return None

async def get_chat_by_code(chat_code: str) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM chats WHERE chat_code = ?", (chat_code,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка получения чата: {e}")
        return None

async def get_active_chat_by_users(customer_id: int, executor_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM chats 
                   WHERE ((customer_id = ? AND executor_id = ?) OR (customer_id = ? AND executor_id = ?)) 
                   AND status = 'active'""",
                (customer_id, executor_id, executor_id, customer_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка поиска чата: {e}")
        return None

async def get_user_active_chat(user_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chats WHERE (customer_id = ? OR executor_id = ?) AND status = 'active'",
                (user_id, user_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка поиска чата пользователя: {e}")
        return None

async def save_message(chat_code: str, sender_id: int, receiver_id: int, message_text: str, message_type: str = 'text', file_id: str = None) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                """INSERT INTO messages 
                   (chat_code, sender_id, receiver_id, message_text, message_type, file_id, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chat_code, sender_id, receiver_id, message_text, message_type, file_id, datetime.now().isoformat())
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {e}")
        return False

async def get_chat_messages(chat_code: str, limit: int = 200) -> list:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM messages WHERE chat_code = ? ORDER BY created_at ASC LIMIT ?",
                (chat_code, limit)
            )
            return [dict(row) for row in await cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения сообщений: {e}")
        return []

async def close_chat(chat_code: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "UPDATE chats SET status = 'closed', closed_at = ? WHERE chat_code = ?",
                (datetime.now().isoformat(), chat_code)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка закрытия чата: {e}")
        return False

async def is_user_banned(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка проверки бана: {e}")
        return False

async def ban_user(user_id: int, reason: str = None) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "UPDATE chats SET status = 'banned' WHERE customer_id = ? OR executor_id = ?",
                (user_id, user_id)
            )
            await db.execute(
                "INSERT OR REPLACE INTO banned_users (user_id, banned_at, reason) VALUES (?, ?, ?)",
                (user_id, datetime.now().isoformat(), reason)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка бана пользователя: {e}")
        return False


async def get_chat_by_codes(code1: str, code2: str) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM chats 
                   WHERE (customer_profile_code = ? AND executor_profile_code = ?)
                   OR (customer_profile_code = ? AND executor_profile_code = ?)""",
                (code1, code2, code2, code1)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Ошибка поиска чата: {e}")
        return None


async def get_or_create_chat(customer_code: str, executor_code: str) -> dict:
    chat = await get_chat_by_codes(customer_code, executor_code)
    if chat:
        return chat
    
    chat_code = f"{customer_code}_{executor_code}"
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                """INSERT INTO chats (chat_code, customer_profile_code, executor_profile_code, status)
                   VALUES (?, ?, ?, 'active')""",
                (chat_code, customer_code, executor_code)
            )
            await db.commit()
        
        return await get_chat_by_codes(customer_code, executor_code)
    except Exception as e:
        logger.error(f"Ошибка создания чата: {e}")
        return None


async def get_user_active_chats(user_code: str) -> list:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM chats 
                   WHERE (customer_profile_code = ? OR executor_profile_code = ?) 
                   AND status = 'active'""",
                (user_code, user_code)
            )
            return [dict(row) for row in await cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения чатов пользователя: {e}")
        return []


async def save_reaction(profile_code: str, user_id: int, reaction: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "INSERT OR REPLACE INTO reactions (profile_code, user_id, reaction) VALUES (?, ?, ?)",
                (profile_code, user_id, reaction)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения реакции: {e}")
        return False

async def get_reactions(profile_code: str) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute(
                "SELECT reaction, COUNT(*) FROM reactions WHERE profile_code = ? GROUP BY reaction",
                (profile_code,)
            )
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.error(f"Ошибка получения реакций: {e}")
        return {}


async def save_review(executor_code: str, customer_name: str, review_text: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute(
                "INSERT INTO reviews (executor_profile_code, customer_name, review_text, created_at) VALUES (?, ?, ?, ?)",
                (executor_code, customer_name, review_text, datetime.now().isoformat())
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения отзыва: {e}")
        return False

async def get_reviews(executor_code: str) -> list:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute(
                "SELECT customer_name, review_text, created_at FROM reviews WHERE executor_profile_code = ? ORDER BY created_at DESC",
                (executor_code,)
            )
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения отзывов: {e}")
        return []

async def has_accepted_response(customer_id: int, executor_profile_code: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            cursor = await db.execute(
                """SELECT 1 FROM chats 
                   WHERE customer_id = ? 
                   AND executor_profile_code = ? 
                   AND status = 'active'""",
                (customer_id, executor_profile_code)
            )
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка проверки принятого отклика: {e}")
        return False


from datetime import datetime, timedelta

async def get_current_week_start() -> str:
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    return week_start.isoformat()

async def update_activity(user_id: int, action_type: str) -> None:
    week_start = await get_current_week_start()
    
    scores = {
        'scroll': 0.5,
        'reaction': 1.0,
        'action': 2.0
    }
    
    score = scores.get(action_type, 0)
    
    async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
        cursor = await db.execute(
            "SELECT 1 FROM user_activity WHERE user_id = ? AND week_start = ?",
            (user_id, week_start)
        )
        exists = await cursor.fetchone()
        
        if exists:
            if action_type == 'scroll':
                await db.execute(
                    "UPDATE user_activity SET scrolls = scrolls + 1, total_score = total_score + ? WHERE user_id = ? AND week_start = ?",
                    (score, user_id, week_start)
                )
            elif action_type == 'reaction':
                await db.execute(
                    "UPDATE user_activity SET reactions = reactions + 1, total_score = total_score + ? WHERE user_id = ? AND week_start = ?",
                    (score, user_id, week_start)
                )
            else:
                await db.execute(
                    "UPDATE user_activity SET actions = actions + 1, total_score = total_score + ? WHERE user_id = ? AND week_start = ?",
                    (score, user_id, week_start)
                )
        else:
            scrolls = 1 if action_type == 'scroll' else 0
            reactions = 1 if action_type == 'reaction' else 0
            actions = 1 if action_type == 'action' else 0
            await db.execute(
                "INSERT INTO user_activity (user_id, week_start, scrolls, reactions, actions, total_score) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, week_start, scrolls, reactions, actions, score)
            )
        await db.commit()


async def get_user_activity_score(user_id: int) -> float:
    week_start = await get_current_week_start()
    async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
        cursor = await db.execute(
            "SELECT total_score FROM user_activity WHERE user_id = ? AND week_start = ?",
            (user_id, week_start)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0.0

async def get_all_activity_scores() -> dict:
    week_start = await get_current_week_start()
    async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
        cursor = await db.execute(
            "SELECT user_id, total_score FROM user_activity WHERE week_start = ?",
            (week_start,)
        )
        return {row[0]: row[1] for row in await cursor.fetchall()}
