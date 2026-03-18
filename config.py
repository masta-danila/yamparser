# ============================================================================
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ============================================================================

# Настройки Google Sheets (список таблиц для обработки)
SPREADSHEETS = [
    "https://docs.google.com/spreadsheets/d/1WcHvb3dcwYnmK_De6Z6DW1NH3uf_Sz0N1-fLLlcpgNE"
]

CREDENTIALS_FILE = "credentials.json"

# Настройки парсинга
DEVICE_TYPE = "mobile"                  # Тип устройства: "mobile" или "desktop"
TWO_GIS_DEVICE_TYPE = "mobile"          # Для 2GIS: "mobile" или "desktop"
WAIT_TIME = 3                           # Время ожидания в секундах
MAX_DAYS_BACK = 30                      # Максимальное количество дней назад для первичного парсинга
MAX_REVIEWS_LIMIT = 1000                 # Максимальное количество отзывов для парсинга
USE_PROXY = True                        # Использовать ли прокси
HEADLESS_MODE = True                    # Скрывать браузеры (True) или показывать (False)

# Настройки Google Sheets
SIMILARITY_THRESHOLD = 0.85             # Порог совпадения текстов (85%)
RECHECK_DAYS = 500                       # Дней для повторной проверки отзывов «Размещен» (если нет на карточке -> «Удален»)

# Настройки потоков
MAX_WORKERS = 2                         # Максимальное количество потоков
DELAY_BETWEEN_WORKERS = 2               # Задержка между запуском потоков (секунды)
DELAY_BETWEEN_URLS = 1                  # Пауза между URL-ами в одном потоке (секунды) 