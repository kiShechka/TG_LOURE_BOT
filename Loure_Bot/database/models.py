
from typing import TypedDict, List, Optional
from datetime import datetime
import sqlite3
import json
import logging
import os

logger = logging.getLogger(__name__)

from config import DB_PATH

class Profile(TypedDict):
    id: Optional[int]
    user_id: int
    username: Optional[str]
    name: str
    industry: str
    description: str
    target: str
    media: List[tuple[str, str]] 
    code: str
    created_at: str 

class AdminChat(TypedDict):
    chat_id: int
    set_at: str 

class UserState(TypedDict):
    user_id: int
    state: Optional[str]
    data: str  
    updated_at: str

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logger.info(f"Инициализация БД по пути: {DB_PATH}")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            description TEXT NOT NULL,
            target TEXT NOT NULL,
            media TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_chats (
            chat_id INTEGER PRIMARY KEY,
            set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_profiles_user_id 
        ON profiles(user_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_profiles_industry 
        ON profiles(industry)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_profiles_target 
        ON profiles(target)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_profiles_created 
        ON profiles(created_at DESC)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ База данных инициализирована успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}", exc_info=True)
        raise

def profile_to_dict(profile: Profile) -> dict:
    try:
        return {
            'user_id': profile['user_id'],
            'username': profile.get('username'),
            'name': profile['name'],
            'industry': profile['industry'],
            'description': profile['description'],
            'target': profile['target'],
            'media': json.dumps(profile.get('media', [])),
            'code': profile['code'],
            'created_at': profile.get('created_at', datetime.now().isoformat())
        }
    except KeyError as e:
        logger.error(f"❌ Ошибка конвертации Profile в dict: отсутствует ключ {e}")
        raise

def dict_to_profile(data: dict) -> Profile:
    try:
        media_json = data.get('media', '[]')
        try:
            media = json.loads(media_json) if media_json else []
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка декодирования media JSON: {e}")
            media = []
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif not created_at:
            created_at = datetime.now().isoformat()
        
        return Profile(
            id=data.get('id'),
            user_id=data['user_id'],
            username=data.get('username'),
            name=data['name'],
            industry=data['industry'],
            description=data['description'],
            target=data['target'],
            media=media,
            code=data['code'],
            created_at=created_at
        )
    except KeyError as e:
        logger.error(f"❌ Ошибка конвертации dict в Profile: отсутствует ключ {e}")
        raise

def save_user_state(user_id: int, state: str, data: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_states (user_id, state, data, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, state, json.dumps(data)))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния пользователя: {e}")
        return False

def load_user_state(user_id: int) -> Optional[UserState]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_states WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserState(
                user_id=row[0],
                state=row[1],
                data=row[2],
                updated_at=row[3]
            )
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки состояния пользователя: {e}")
        return None

def delete_user_state(user_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления состояния пользователя: {e}")
        return False
