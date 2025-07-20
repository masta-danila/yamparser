#!/usr/bin/env python3
"""
Простой тест импорта selenium-wire
"""

print("Тестируем импорт selenium-wire...")

# Тест 1: Прямой импорт
try:
    import seleniumwire
    print("✅ Модуль seleniumwire импортирован")
    print(f"   Версия: {seleniumwire.__version__ if hasattr(seleniumwire, '__version__') else 'неизвестна'}")
except ImportError as e:
    print(f"❌ Ошибка импорта seleniumwire: {e}")

# Тест 2: Импорт webdriver
try:
    from seleniumwire import webdriver as wiredriver
    print("✅ seleniumwire.webdriver импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта seleniumwire.webdriver: {e}")

# Тест 3: Повторяем логику из driver_manager.py
try:
    from seleniumwire import webdriver as wiredriver
    SELENIUMWIRE_AVAILABLE = True
    print("✅ SELENIUMWIRE_AVAILABLE = True")
except ImportError:
    SELENIUMWIRE_AVAILABLE = False
    wiredriver = None
    print("❌ SELENIUMWIRE_AVAILABLE = False")

# Тест 4: Проверяем proxy_manager
try:
    from proxy_manager import ProxyManagerSeleniumWire
    PROXY_AVAILABLE = True
    print("✅ ProxyManagerSeleniumWire импортирован")
except ImportError as e:
    PROXY_AVAILABLE = False
    print(f"❌ Ошибка импорта ProxyManagerSeleniumWire: {e}")

print(f"\nИтого:")
print(f"SELENIUMWIRE_AVAILABLE: {SELENIUMWIRE_AVAILABLE}")
print(f"PROXY_AVAILABLE: {PROXY_AVAILABLE}")

# Тест 5: Попробуем создать proxy manager
if SELENIUMWIRE_AVAILABLE and PROXY_AVAILABLE:
    try:
        proxy_manager = ProxyManagerSeleniumWire()
        stats = proxy_manager.get_stats()
        print(f"✅ Прокси менеджер создан, загружено прокси: {stats['total_proxies']}")
    except Exception as e:
        print(f"❌ Ошибка создания прокси менеджера: {e}") 