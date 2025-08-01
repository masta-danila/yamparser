# ============================================================================
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ============================================================================

# Настройки Google Sheets (список таблиц для обработки)
SPREADSHEETS = [
    "https://docs.google.com/spreadsheets/d/1WcHvb3dcwYnmK_De6Z6DW1NH3uf_Sz0N1-fLLlcpgNE"
]

CREDENTIALS_FILE = "credentials.json"

# Настройки базы данных PostgreSQL
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'reviews',
    'user': 'daniladzhiev',
    'password': '021682'  # ЗАМЕНИТЕ НА ВАШ ПАРОЛЬ!
}

# Настройки базы данных
WRITE_TO_DATABASE = False                # Записывать ли данные в БД (если False - только фильтрация по MAX_DAYS_BACK без чекпоинта)

# Настройки парсинга
DEVICE_TYPE = "mobile"                  # Тип устройства: "mobile" или "desktop"
WAIT_TIME = 3                           # Время ожидания в секундах
MAX_DAYS_BACK = 30                      # Максимальное количество дней назад для первичного парсинга
MAX_REVIEWS_LIMIT = 1000                 # Максимальное количество отзывов для парсинга
USE_PROXY = True                        # Использовать ли прокси
HEADLESS_MODE = False                   # Скрывать браузеры (True) или показывать (False)

# Настройки Google Sheets
SIMILARITY_THRESHOLD = 0.85             # Порог совпадения текстов (85%)

# Настройки потоков
MAX_WORKERS = 20                         # Максимальное количество потоков
DELAY_BETWEEN_WORKERS = 2               # Задержка между запуском потоков (секунды)
DELAY_BETWEEN_URLS = 1                  # Пауза между URL-ами в одном потоке (секунды) 