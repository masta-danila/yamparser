#!/usr/bin/env python3
"""
Финальный тест прокси с подробной диагностикой
Тестирует рабочий метод seleniumwire из proxy-seller.io
"""

import os
import sys
import time
import json
from proxy_manager_seleniumwire import ProxyManagerSeleniumWire

def test_proxy_detailed(proxy_manager, proxy_data, test_name=""):
    """Подробный тест прокси с диагностикой"""
    print(f"\n{'='*70}")
    print(f"🧪 ТЕСТ: {test_name}")
    print(f"📋 Прокси: {proxy_data['ip']}:{proxy_data['port']}")
    print(f"👤 Логин: {proxy_data['username']}")
    print(f"🔑 Пароль: {proxy_data['password']}")
    print(f"{'='*70}")
    
    try:
        # Создаем драйвер с прокси
        print("🔧 Создаем WebDriver с seleniumwire...")
        driver = proxy_manager.create_seleniumwire_driver(proxy_data, headless=True)
        
        print("🌐 Переходим на httpbin.org/ip...")
        driver.get("https://httpbin.org/ip")
        time.sleep(3)
        
        # Получаем ответ
        page_source = driver.page_source
        print(f"📄 Получен ответ: {page_source[:300]}...")
        
        # Пытаемся извлечь IP из JSON
        try:
            import re
            json_match = re.search(r'\{[^}]*"origin"[^}]*\}', page_source)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                returned_ip = data.get('origin', 'Не найден')
                print(f"🔍 Извлеченный IP: {returned_ip}")
                
                # Проверяем результат
                expected_proxy_ip = proxy_data['ip']
                if expected_proxy_ip in returned_ip:
                    print(f"✅ УСПЕХ! Прокси работает - IP изменился на {returned_ip}")
                    result = True
                else:
                    print(f"❌ НЕУДАЧА! Прокси не работает:")
                    print(f"   Ожидался IP: {expected_proxy_ip}")
                    print(f"   Получен IP: {returned_ip}")
                    result = False
            else:
                print("❌ Не удалось найти JSON с IP в ответе")
                result = False
                
        except Exception as e:
            print(f"❌ Ошибка парсинга ответа: {e}")
            result = False
        
        driver.quit()
        return result
        
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        try:
            driver.quit()
        except:
            pass
        return False

def test_without_proxy():
    """Тест без прокси для сравнения"""
    print(f"\n{'='*70}")
    print(f"🧪 КОНТРОЛЬНЫЙ ТЕСТ БЕЗ ПРОКСИ")
    print(f"{'='*70}")
    
    try:
        from seleniumwire import webdriver as wiredriver
        from selenium.webdriver.chrome.options import Options
        
        # Настройки Chrome без прокси
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")
        
        print("🔧 Создаем WebDriver без прокси...")
        driver = wiredriver.Chrome(options=options)
        
        print("🌐 Переходим на httpbin.org/ip...")
        driver.get("https://httpbin.org/ip")
        time.sleep(2)
        
        page_source = driver.page_source
        print(f"📄 Получен ответ: {page_source[:300]}...")
        
        # Извлекаем IP
        import re, json
        json_match = re.search(r'\{[^}]*"origin"[^}]*\}', page_source)
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
            real_ip = data.get('origin', 'Не найден')
            print(f"🔍 Реальный IP: {real_ip}")
        
        driver.quit()
        return real_ip
        
    except Exception as e:
        print(f"❌ Ошибка в контрольном тесте: {e}")
        try:
            driver.quit()
        except:
            pass
        return None

def main():
    print("🚀 ФИНАЛЬНЫЙ ТЕСТ ПРОКСИ С SELENIUMWIRE")
    print("Основан на рабочих методах proxy-seller.io")
    print("=" * 80)
    
    # Сначала тест без прокси
    real_ip = test_without_proxy()
    
    # Инициализируем менеджер прокси
    proxy_manager = ProxyManagerSeleniumWire()
    
    if not proxy_manager.proxies:
        print("❌ Нет доступных прокси для тестирования")
        return
    
    # Тестируем первые 3 прокси
    test_proxies = proxy_manager.proxies[:3]
    successful_proxies = []
    
    for i, proxy in enumerate(test_proxies, 1):
        test_name = f"Прокси #{i} - {proxy['ip']}:{proxy['port']}"
        
        if test_proxy_detailed(proxy_manager, proxy, test_name):
            successful_proxies.append(proxy)
            print(f"✅ Прокси #{i} добавлен в список рабочих")
        else:
            print(f"❌ Прокси #{i} не работает")
        
        time.sleep(1)  # Небольшая пауза между тестами
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    print(f"🏠 Реальный IP (без прокси): {real_ip}")
    print(f"📋 Всего протестировано прокси: {len(test_proxies)}")
    print(f"✅ Рабочих прокси: {len(successful_proxies)}")
    print(f"❌ Нерабочих прокси: {len(test_proxies) - len(successful_proxies)}")
    
    if successful_proxies:
        print(f"\n🎉 РАБОЧИЕ ПРОКСИ:")
        for i, proxy in enumerate(successful_proxies, 1):
            print(f"   {i}. {proxy['ip']}:{proxy['port']} (логин: {proxy['username']})")
        
        print(f"\n✅ МЕТОД SELENIUMWIRE РАБОТАЕТ!")
        print(f"💡 Используйте proxy_manager_seleniumwire.py в основном парсере")
    else:
        print(f"\n❌ НИ ОДИН ПРОКСИ НЕ РАБОТАЕТ")
        print(f"💡 Проверьте:")
        print(f"   - Правильность данных прокси")
        print(f"   - Доступность прокси серверов")
        print(f"   - Настройки сети")
    
    print(f"\n{'='*80}")
    print("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    main() 