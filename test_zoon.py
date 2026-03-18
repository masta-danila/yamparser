#!/usr/bin/env python3
"""
Тест Zoon: открывает URL и ждёт Enter для инспектирования.
Запуск: python test_zoon.py
"""
import sys

DEFAULT_URL = "https://zoon.ru/s/8R7C2Q"

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    from platforms import get_handler_for_url

    handler = get_handler_for_url(url)
    if not handler:
        print(f"❌ Платформа не определена для URL: {url}")
        sys.exit(1)
    print(f"📌 Платформа: {handler.name}")
    result = handler.get_reviews(url=url, use_proxy=True)
    print(f"Готово: {result}")
