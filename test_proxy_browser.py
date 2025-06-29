#!/usr/bin/env python3
"""
Тестовый файл для проверки прокси через браузер
Использует рабочий метод seleniumwire
"""

import time
import json
import re
from proxy_manager_seleniumwire import ProxyManagerSeleniumWire

def test_proxy_in_browser(proxy_data, headless=False, test_duration=30):
    """
    Тестирование прокси в браузере с визуальной проверкой
    
    Args:
        proxy_data: данные прокси
        headless: запускать в headless режиме
        test_duration: время показа браузера в секундах
    """
    print(f"\n{'='*70}")
    print(f"🧪 ТЕСТ ПРОКСИ В БРАУЗЕРЕ")
    print(f"📋 Прокси: {proxy_data['ip']}:{proxy_data['port']}")
    print(f"👤 Логин: {proxy_data['username']}")
    print(f"🔑 Пароль: {proxy_data['password']}")
    print(f"⏱️ Время показа: {test_duration} секунд")
    print(f"{'='*70}")
    
    proxy_manager = ProxyManagerSeleniumWire()
    driver = None
    
    try:
        # Создаем драйвер с прокси
        print("🔧 Создаем браузер с прокси...")
        driver = proxy_manager.create_seleniumwire_driver(proxy_data, headless=headless)
        
        # Тест 1: Проверка IP
        print("\n📍 Тест 1: Проверка IP адреса")
        print("🌐 Переходим на httpbin.org/ip...")
        driver.get("https://httpbin.org/ip")
        time.sleep(3)
        
        # Извлекаем IP из страницы
        page_source = driver.page_source
        json_match = re.search(r'\{[^}]*"origin"[^}]*\}', page_source)
        
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
            current_ip = data.get('origin', 'Не определен')
            
            print(f"✅ Текущий IP: {current_ip}")
            
            if current_ip != "147.45.255.191":  # Ваш реальный IP
                print(f"✅ ПРОКСИ РАБОТАЕТ! IP изменился с реального на {current_ip}")
                proxy_working = True
            else:
                print(f"❌ Прокси не работает - показывается реальный IP")
                proxy_working = False
        else:
            print("❌ Не удалось извлечь IP из ответа")
            proxy_working = False
        
        if not headless:
            print(f"\n⏱️ Браузер будет открыт {test_duration} секунд для визуальной проверки...")
            print("👀 Вы можете визуально проверить IP на странице")
            
            # Тест 2: Проверка на другом сайте
            print("\n📍 Тест 2: Проверка на whatismyipaddress.com")
            driver.get("https://whatismyipaddress.com/")
            time.sleep(3)
            
            # Тест 3: Проверка на 2ip.ru
            print("\n📍 Тест 3: Проверка на 2ip.ru")
            driver.get("https://2ip.ru/")
            time.sleep(3)
            
            print(f"\n⏳ Ожидание {test_duration} секунд...")
            print("🔍 Проверьте IP адреса на открытых страницах")
            time.sleep(test_duration)
        
        return proxy_working
        
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        return False
        
    finally:
        if driver:
            print("🔒 Закрываем браузер...")
            driver.quit()

def test_without_proxy(headless=False, test_duration=15):
    """Тест без прокси для сравнения"""
    print(f"\n{'='*70}")
    print(f"🧪 КОНТРОЛЬНЫЙ ТЕСТ БЕЗ ПРОКСИ")
    print(f"⏱️ Время показа: {test_duration} секунд")
    print(f"{'='*70}")
    
    proxy_manager = ProxyManagerSeleniumWire()
    driver = None
    
    try:
        # Создаем драйвер без прокси
        print("🔧 Создаем браузер без прокси...")
        driver = proxy_manager.create_seleniumwire_driver(None, headless=headless)
        
        print("🌐 Переходим на httpbin.org/ip...")
        driver.get("https://httpbin.org/ip")
        time.sleep(2)
        
        # Извлекаем реальный IP
        page_source = driver.page_source
        json_match = re.search(r'\{[^}]*"origin"[^}]*\}', page_source)
        
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
            real_ip = data.get('origin', 'Не определен')
            print(f"🏠 Ваш реальный IP: {real_ip}")
        
        if not headless:
            print(f"\n⏳ Ожидание {test_duration} секунд для сравнения...")
            time.sleep(test_duration)
        
        return real_ip
        
    except Exception as e:
        print(f"❌ Ошибка в контрольном тесте: {e}")
        return None
        
    finally:
        if driver:
            driver.quit()

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ПРОКСИ В БРАУЗЕРЕ")
    print("Основано на рабочем методе seleniumwire")
    print("=" * 80)
    
    # Инициализируем менеджер прокси
    proxy_manager = ProxyManagerSeleniumWire()
    
    if not proxy_manager.proxies:
        print("❌ Нет доступных прокси для тестирования")
        return
    
    # Настройки тестирования
    headless_mode = False  # Показываем браузер
    test_duration = 30     # Секунд показа браузера
    
    print(f"\n⚙️ Настройки тестирования:")
    print(f"   Headless режим: {'Да' if headless_mode else 'Нет (браузер будет виден)'}")
    print(f"   Время показа браузера: {test_duration} секунд")
    print(f"   Доступно прокси: {len(proxy_manager.proxies)}")
    
    # Сначала тест без прокси
    print(f"\n🏠 Сначала определяем ваш реальный IP...")
    real_ip = test_without_proxy(headless=True, test_duration=5)
    
    # Тестируем первые 3 прокси
    test_proxies = proxy_manager.proxies[:3]
    successful_tests = 0
    
    for i, proxy in enumerate(test_proxies, 1):
        print(f"\n🔄 Тестируем прокси {i}/{len(test_proxies)}")
        
        if test_proxy_in_browser(proxy, headless=headless_mode, test_duration=test_duration):
            successful_tests += 1
            print(f"✅ Прокси {i} работает!")
        else:
            print(f"❌ Прокси {i} не работает")
        
        # Небольшая пауза между тестами
        if i < len(test_proxies):
            print(f"\n⏸️ Пауза 3 секунды перед следующим тестом...")
            time.sleep(3)
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    print(f"🏠 Ваш реальный IP: {real_ip}")
    print(f"📋 Протестировано прокси: {len(test_proxies)}")
    print(f"✅ Рабочих прокси: {successful_tests}")
    print(f"❌ Нерабочих прокси: {len(test_proxies) - successful_tests}")
    print(f"📈 Процент успеха: {(successful_tests/len(test_proxies)*100):.1f}%")
    
    if successful_tests > 0:
        print(f"\n🎉 ОТЛИЧНО! У вас есть {successful_tests} рабочих прокси!")
        print(f"💡 Можете использовать их в основном парсере")
    else:
        print(f"\n😞 К сожалению, ни один прокси не работает")
        print(f"💡 Проверьте настройки прокси или обратитесь к провайдеру")
    
    print(f"\n{'='*80}")
    print("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    main() 