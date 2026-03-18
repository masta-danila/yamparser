#!/usr/bin/env python3
"""
Скрипт для тестирования 2GIS — открывает URL и останавливается для инспектирования DOM.
Запуск: python test_2gis.py [URL]
Пример: python test_2gis.py https://2gis.ru/moscow/firm/70000001088869867
"""

import sys
from driver_manager import initialize_profiles_cleanup, cleanup_all_profiles

# URL по умолчанию
DEFAULT_URL = "https://2gis.ru/moscow/firm/70000001088869867"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"🚀 Тест 2GIS: {url}\n")

    initialize_profiles_cleanup()

    from platforms import get_handler_for_url
    handler = get_handler_for_url(url)
    if not handler or not handler.can_handle(url):
        print(f"❌ URL не распознан как 2GIS: {url}")
        return

    result = handler.get_reviews(
        url=url,
        device_type="mobile",
        use_proxy=True,
    )

    print(f"\n📊 Результат: success={result.get('success')}, error={result.get('error')}")
    cleanup_all_profiles()


if __name__ == "__main__":
    main()
