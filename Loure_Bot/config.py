import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import logging
logger = logging.getLogger(__name__)
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    error_msg = "❌ TELEGRAM_BOT_TOKEN не найден в .env файле!"
    logger.error(error_msg)
    raise ValueError(error_msg)

TOKEN = TOKEN.strip()

ADMIN_CHAT_ID: Optional[int] = None
admin_chat_str = os.getenv('ADMIN_CHAT_ID')

if admin_chat_str:
    try:
        ADMIN_CHAT_ID = int(admin_chat_str.strip())
        logger.info(f"✅ ADMIN_CHAT_ID загружен: {ADMIN_CHAT_ID}")
    except ValueError:
        logger.warning(f"⚠️ Неверный формат ADMIN_CHAT_ID: {admin_chat_str}")
        ADMIN_CHAT_ID = None
else:
    logger.info("ℹ️ ADMIN_CHAT_ID не задан, админские уведомления отключены")

ADMIN_IDS: list[int] = []
if os.getenv('ADMIN_IDS'):
    try:
        ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS').split(',') if id.strip()]
        logger.info(f"✅ Загружено администраторов: {len(ADMIN_IDS)}")
    except Exception as e:
        logger.error(f"Ошибка парсинга ADMIN_IDS: {e}")

INDUSTRIES: Dict[str, Dict[str, Any]] = {
    'artist': {
        'name': 'Художник',
        'max_files': 8,
        'file_type': ['photo' 'video'],
        'examples': 'Иллюстрации, Анимация, Дизайн',
        'instruction': 'Пришли 8 фото/видео примеров работ'
    },
    'writer': {
        'name': 'Писатель',
        'max_files': 8,
        'file_type': ['photo' 'video'],
        'examples': 'Стихи, Рассказы, Биографии',
        'instruction': 'Пришли 8 фото/видео примеров работ'
    },
    'musician': {
        'name': 'Музыкант',
        'max_files': 8,
        'file_type': 'video',
        'examples': 'Песни, Озвучка, Саунд-дизайн',
        'instruction': 'Отправь 8 клипов с твоей музыкой'
    }
}

TARGETS: Dict[str, str] = {
    'client': 'Заказчика',
    'audience': 'Аудиторию',
    'team': 'Команду',
    'executor': 'Исполнителя'
}

TARGET_MATCHING: Dict[str, str] = {
    'client': 'executor',
    'executor': 'client',
    'audience': 'audience',
    'team': 'team'
}

DB_NAME = 'bot_database.db'
DB_TIMEOUT = 30  # seconds
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)

MAX_PHOTOS = 8
MAX_AUDIOS = 4
MAX_DESCRIPTION_LENGTH = 1000
MAX_NAME_LENGTH = 100


POLLING_TIMEOUT = 30
POLLING_LIMIT = 100


PARSE_MODE = "HTML"  

MESSAGES = {
    'start': "👋 Привет! Я бот для творческих знакомств.",
    'profile_created': "✅ Анкета успешно создана!",
    'profile_updated': "✅ Анкета успешно обновлена!",
    'profile_deleted': "✅ Анкета удалена!",
    'no_profile': "❌ У вас еще нет анкеты.",
    'error': "⚠️ Произошла ошибка. Попробуйте еще раз.",
    'cancel': "🚫 Действие отменено.",
    'access_denied': "⛔️ У вас нет доступа к этой команде."
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')

os.makedirs(LOG_DIR, exist_ok=True)

def check_config() -> bool:
    errors = []
    
    if not TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не задан")
    
    if not TOKEN.startswith('') or len(TOKEN) < 10:
        errors.append("Неверный формат TELEGRAM_BOT_TOKEN")
    
    env_path = os.path.join(BASE_DIR, '.env')
    if not os.path.exists(env_path):
        logger.warning(f"Файл .env не найден по пути: {env_path}")
    
    if errors:
        logger.error(f"Ошибки конфигурации: {errors}")
        return False
    
    logger.info("✅ Конфигурация загружена успешно")
    return True
check_config()
