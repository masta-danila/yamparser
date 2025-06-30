#!/usr/bin/env python3
"""
Обновленный модуль для управления прокси серверами с поддержкой seleniumwire
Основан на рабочих методах из proxy-seller.io
"""

import random
import time
import requests
from typing import List, Dict, Optional, Tuple
import threading
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions

class ProxyManagerSeleniumWire:
    """Менеджер прокси серверов с поддержкой seleniumwire"""
    
    def __init__(self, proxy_file: str = "proxy.txt"):
        """
        Инициализация менеджера прокси
        
        Args:
            proxy_file: путь к файлу с прокси
        """
        self.proxy_file = proxy_file
        self.proxies = []
        self.current_index = 0
        self.lock = threading.Lock()
        
        # Загружаем прокси при инициализации
        self.load_proxies()
        
    def load_proxies(self) -> None:
        """Загрузить прокси из файла"""
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.proxies = []
            skipped_lines = 0
            
            for line_num, line in enumerate(lines, 1):
                original_line = line
                line = line.strip()
                
                if not line or line.startswith('#'):  # Игнорируем комментарии и пустые строки
                    continue
                    
                proxy = self.parse_proxy_line(line)
                if proxy:
                    self.proxies.append(proxy)
                else:
                    skipped_lines += 1
                    print(f"⚠️ Строка {line_num} пропущена (неверный формат): {original_line.strip()}")
            
            print(f"📋 Загружено {len(self.proxies)} прокси из {self.proxy_file}")
            if skipped_lines > 0:
                print(f"⚠️ Пропущено {skipped_lines} строк с неверным форматом")
            
            if not self.proxies:
                print("⚠️ Прокси не найдены, будет использоваться прямое соединение")
                
        except FileNotFoundError:
            print(f"⚠️ Файл {self.proxy_file} не найден")
            print("💡 Создайте файл proxy.txt с прокси в формате:")
            print("   IP:PORT:USERNAME:PASSWORD")
            print("   Пример: 82.97.251.114:16172:nEVzuQ:YKAGuCukum2s")
            self.proxies = []
            
        except Exception as e:
            print(f"❌ Ошибка загрузки прокси: {e}")
            self.proxies = []
    
    def parse_proxy_line(self, line: str) -> Optional[Dict]:
        """
        Парсинг строки прокси в формате: IP:PORT:USERNAME:PASSWORD
        """
        try:
            line = line.strip()
            parts = line.split(':')
            
            if len(parts) == 4:
                # ip:port:username:password
                return {
                    'ip': parts[0],
                    'port': int(parts[1]),
                    'username': parts[2],
                    'password': parts[3],
                    'protocol': 'http'
                }
            else:
                print(f"⚠️ Неверный формат прокси '{line}' (ожидается IP:PORT:USERNAME:PASSWORD)")
                return None
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга прокси '{line}': {e}")
            return None
    
    def get_next_proxy(self) -> Optional[Dict]:
        """
        Получить следующий прокси из списка (ротация)
        
        Returns:
            Словарь с данными прокси или None если нет прокси
        """
        with self.lock:
            if not self.proxies:
                return None
            
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy
    
    def get_random_proxy(self) -> Optional[Dict]:
        """
        Получить случайный прокси из списка
        
        Returns:
            Словарь с данными прокси или None если нет прокси
        """
        if not self.proxies:
            return None
        
        return random.choice(self.proxies)
    
    def configure_seleniumwire_proxy(self, proxy: Dict) -> Tuple[Options, Optional[Dict]]:
        """
        Настройка прокси для seleniumwire (РАБОЧИЙ МЕТОД!)
        
        Args:
            proxy: словарь с данными прокси
            
        Returns:
            Кортеж (chrome_options, seleniumwire_options)
        """
        # Настройки Chrome
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Отключаем WebRTC для предотвращения утечки IP
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-webrtc-hw-encoding")
        options.add_argument("--disable-webrtc-hw-decoding")
        
        # Отключаем предупреждения SSL/сертификатов (убирает "Not secure")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-extensions-http-throttling")
        
        if not proxy:
            print("🌐 Прокси не используется")
            return options, None
        
        # Настройки прокси для seleniumwire (РАБОЧИЙ МЕТОД!)
        proxy_options = {
            'proxy': {
                'http': f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}",
                'https': f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}",
                'no_proxy': 'localhost,127.0.0.1'
            }
        }
        
        print(f"🌐 Настроен прокси: {proxy['ip']}:{proxy['port']} (seleniumwire)")
        return options, proxy_options
    
    def configure_selenium_proxy_legacy(self, proxy: Dict, browser: str = 'chrome') -> Options:
        """
        Настройка прокси для обычного Selenium WebDriver (НЕ РАБОТАЕТ С АУТЕНТИФИКАЦИЕЙ!)
        
        Args:
            proxy: словарь с данными прокси
            browser: тип браузера ('chrome' или 'firefox')
            
        Returns:
            Настроенные опции браузера
        """
        if browser.lower() == 'chrome':
            options = Options()
            
            if proxy:
                # Формируем строку прокси (формат: IP:PORT:USERNAME:PASSWORD)
                # Экранируем символы для Selenium
                import urllib.parse
                username = urllib.parse.quote(proxy['username'], safe='')
                password = urllib.parse.quote(proxy['password'], safe='')
                proxy_string = f"http://{username}:{password}@{proxy['ip']}:{proxy['port']}"
                
                options.add_argument(f'--proxy-server={proxy_string}')
                print(f"🌐 Используется прокси (legacy): {proxy['ip']}:{proxy['port']}")
            
            return options
            
        elif browser.lower() == 'firefox':
            options = FirefoxOptions()
            
            if proxy:
                # Firefox использует другой способ настройки прокси
                options.set_preference("network.proxy.type", 1)
                
                if proxy['protocol'] == 'http':
                    options.set_preference("network.proxy.http", proxy['ip'])
                    options.set_preference("network.proxy.http_port", proxy['port'])
                    options.set_preference("network.proxy.ssl", proxy['ip'])
                    options.set_preference("network.proxy.ssl_port", proxy['port'])
                elif proxy['protocol'] == 'socks5':
                    options.set_preference("network.proxy.socks", proxy['ip'])
                    options.set_preference("network.proxy.socks_port", proxy['port'])
                    options.set_preference("network.proxy.socks_version", 5)
                
                if proxy['username'] and proxy['password']:
                    options.set_preference("network.proxy.socks_username", proxy['username'])
                    options.set_preference("network.proxy.socks_password", proxy['password'])
                
                print(f"🌐 Используется прокси (legacy): {proxy['ip']}:{proxy['port']}")
            
            return options
        
        else:
            raise ValueError(f"Неподдерживаемый браузер: {browser}")
    
    def create_seleniumwire_driver(self, proxy: Optional[Dict] = None, headless: bool = False):
        """
        Создать WebDriver с seleniumwire и прокси (РАБОЧИЙ МЕТОД!)
        
        Args:
            proxy: словарь с данными прокси (если None, то берется следующий из ротации)
            headless: запускать браузер в headless режиме
            
        Returns:
            Настроенный WebDriver
        """
        try:
            from seleniumwire import webdriver as wiredriver
        except ImportError:
            raise ImportError("seleniumwire не установлен. Установите: pip install selenium-wire")
        
        # Получаем прокси если не передан
        if proxy is None:
            proxy = self.get_next_proxy()
        
        # Настраиваем опции
        chrome_options, proxy_options = self.configure_seleniumwire_proxy(proxy)
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Создаем драйвер
        if proxy_options:
            driver = wiredriver.Chrome(
                options=chrome_options,
                seleniumwire_options=proxy_options
            )
        else:
            driver = wiredriver.Chrome(options=chrome_options)
        
        # Убираем признаки автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def test_proxy_with_seleniumwire(self, proxy: Dict) -> bool:
        """
        Тестирование прокси с помощью seleniumwire
        
        Args:
            proxy: словарь с данными прокси
            
        Returns:
            True если прокси работает, False в противном случае
        """
        try:
            print(f"🧪 Тестируем прокси {proxy['ip']}:{proxy['port']} с seleniumwire...")
            
            driver = self.create_seleniumwire_driver(proxy, headless=True)
            
            # Тестируем на httpbin.org/ip
            driver.get("https://httpbin.org/ip")
            time.sleep(2)
            
            page_source = driver.page_source
            driver.quit()
            
            # Проверяем, что IP изменился
            if proxy['ip'] in page_source:
                print(f"✅ Прокси {proxy['ip']}:{proxy['port']} работает!")
                return True
            else:
                print(f"❌ Прокси {proxy['ip']}:{proxy['port']} не работает (IP не изменился)")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка тестирования прокси {proxy['ip']}:{proxy['port']}: {e}")
            try:
                driver.quit()
            except:
                pass
            return False
    
    def get_stats(self) -> Dict:
        """
        Получить статистику по прокси
        
        Returns:
            Словарь со статистикой
        """
        return {
            'total_proxies': len(self.proxies),
            'current_index': self.current_index
        }

def create_example_proxy_file():
    """Создать пример файла proxy.txt"""
    example_content = """# Формат прокси: IP:PORT:USERNAME:PASSWORD
# Каждая строка - один прокси
82.97.251.114:16172:nEVzuQ:YKAGuCukum2s
203.0.113.10:3128:user1:pass1
198.51.100.20:8080:user2:pass2
192.168.1.100:1080:user3:pass3

# Комментарии начинаются с #
# Пустые строки игнорируются
"""
    
    try:
        with open('proxy.txt', 'w', encoding='utf-8') as f:
            f.write(example_content)
        print("📄 Создан пример файла proxy.txt")
        print("✏️ Отредактируйте его, добавив свои прокси")
    except Exception as e:
        print(f"❌ Ошибка создания файла proxy.txt: {e}")

if __name__ == "__main__":
    # Пример использования
    print("🔧 Демонстрация менеджера прокси с seleniumwire...")
    
    # Создаем пример файла если его нет
    import os
    if not os.path.exists('proxy.txt'):
        create_example_proxy_file()
    
    # Инициализируем менеджер
    proxy_manager = ProxyManagerSeleniumWire()
    
    # Показываем статистику
    stats = proxy_manager.get_stats()
    print(f"\n📊 Статистика: {stats}")
    
    # Пример получения прокси
    if proxy_manager.proxies:
        proxy = proxy_manager.get_next_proxy()
        print(f"\n🌐 Первый прокси: {proxy['ip']}:{proxy['port']}")
        
        # Тестируем прокси
        print("\n🧪 Тестирование прокси...")
        if proxy_manager.test_proxy_with_seleniumwire(proxy):
            print("✅ Прокси работает!")
        else:
            print("❌ Прокси не работает")
        
        # Показываем настройку для seleniumwire
        chrome_options, proxy_options = proxy_manager.configure_seleniumwire_proxy(proxy)
        print("✅ Опции Chrome и seleniumwire настроены")
    else:
        print("\n⚠️ Нет доступных прокси") 