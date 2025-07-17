# ============================================================================
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ============================================================================

# Настройки Google Sheets (список таблиц для обработки)
SPREADSHEETS = [
    "https://docs.google.com/spreadsheets/d/1d9uG0ml8EiXM_wdtohXsDjjSPYX6-n3BdYDyjPK0f7o/",
    "https://docs.google.com/spreadsheets/d/1eMEBYO-0hNgzh0tLJ1TytDMVZ_MpgWeFkyCTpv_w4nY/"
]

CREDENTIALS_FILE = "credentials.json"

# Настройки базы данных
WRITE_TO_DATABASE = True                # Записывать ли данные в БД (если False - только фильтрация по MAX_DAYS_BACK без чекпоинта)

# Настройки парсинга
DEVICE_TYPE = "mobile"                  # Тип устройства: "mobile" или "desktop"
WAIT_TIME = 3                           # Время ожидания в секундах
MAX_DAYS_BACK = 30                      # Максимальное количество дней назад для первичного парсинга
MAX_REVIEWS_LIMIT = 1000                 # Максимальное количество отзывов для парсинга
USE_PROXY = True                        # Использовать ли прокси

# Настройки Google Sheets
SIMILARITY_THRESHOLD = 0.85             # Порог совпадения текстов (85%)

# Настройки потоков
MAX_WORKERS = 20                         # Максимальное количество потоков
DELAY_BETWEEN_WORKERS = 2               # Задержка между запуском потоков (секунды)
DELAY_BETWEEN_URLS = 1                  # Пауза между URL-ами в одном потоке (секунды) 