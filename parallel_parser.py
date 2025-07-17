import sys
import os
import time
import logging
import threading
import psutil
from threading import Thread, Lock
from typing import List, Dict, Any
from reviews_parser import get_reviews_page_with_retry
from driver_manager import get_driver_creation_lock, initialize_profiles_cleanup, cleanup_all_profiles
from thread_logger import thread_print, get_thread_prefix

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отключаем избыточные логи от сторонних библиотек
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.storage').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.modifier').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.handler').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.proxy').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)

# Оставляем наш логгер на уровне INFO
logger.setLevel(logging.INFO)

# Используем общую блокировку из driver_manager для синхронизации между потоками
driver_creation_lock = get_driver_creation_lock()

# Функция get_thread_prefix теперь импортируется из thread_logger

def monitor_system_resources():
    """Мониторинг системных ресурсов"""
    try:
        # Получаем информацию о системе
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Информация о процессах Chrome
        chrome_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    chrome_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Информация о потоках
        active_threads = threading.active_count()
        
        thread_print(f"📊 СИСТЕМНЫЕ РЕСУРСЫ:")
        thread_print(f"   💻 CPU: {cpu_percent}%")
        thread_print(f"   🧠 RAM: {memory.percent}% ({memory.used / 1024 / 1024 / 1024:.1f}GB / {memory.total / 1024 / 1024 / 1024:.1f}GB)")
        thread_print(f"   🧵 Активных потоков: {active_threads}")
        thread_print(f"   🌐 Chrome процессов: {len(chrome_processes)}")
        
        if chrome_processes:
            total_chrome_memory = sum(p['memory_mb'] for p in chrome_processes)
            thread_print(f"   📈 Chrome память: {total_chrome_memory:.1f}MB")
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'active_threads': active_threads,
            'chrome_processes': len(chrome_processes),
            'chrome_memory_mb': sum(p['memory_mb'] for p in chrome_processes) if chrome_processes else 0
        }
    except Exception as e:
        thread_print(f"❌ Ошибка мониторинга ресурсов: {e}")
        return None

def parse_urls(urls: List[str], num_workers: int = 4, device_type: str = "mobile", 
               wait_time: int = 3, max_days_back: int = 10, max_reviews_limit: int = 2000, 
               use_proxy: bool = True, max_workers: int = 8, delay_between_workers: int = 2, 
               delay_between_urls: int = 3) -> Dict[str, Any]:
    """
    Парсит список URL-ов в параллельном режиме
    
    Args:
        urls: Список URL-ов для парсинга
        num_workers: Количество параллельных потоков (по умолчанию 4)
        device_type: Тип устройства ("mobile" или "desktop")
        wait_time: Время ожидания в секундах
        max_days_back: Максимальное количество дней назад для первичного парсинга
        max_reviews_limit: Максимальное количество отзывов для парсинга
        use_proxy: Использовать ли прокси
        max_workers: Максимальное количество потоков
        delay_between_workers: Задержка между запуском потоков (секунды)
        delay_between_urls: Пауза между URL-ами в одном потоке (секунды)
    
    Returns:
        Словарь с результатами парсинга
    """
    if not urls:
        logger.error("Список URL-ов пустой")
        return {"success": False, "error": "Empty URLs list"}
    
    # Ограничиваем количество воркеров разумным пределом
    actual_workers = min(num_workers, len(urls), max_workers)
    logger.info(f"Запуск парсинга {len(urls)} URL-ов в {actual_workers} потоков")
    
    # Мониторинг ресурсов перед запуском
    thread_print("📊 Мониторинг ресурсов ПЕРЕД запуском потоков:")
    initial_resources = monitor_system_resources()
    
    # Больше не используем менеджер профилей - создаем временные профили
    
    # Распределяем URL-ы между потоками
    url_batches = []
    for i in range(actual_workers):
        batch = []
        # Каждый поток получает свою долю URL-ов
        for j in range(i, len(urls), actual_workers):
            batch.append(urls[j])
        if batch:  # Добавляем только непустые батчи
            url_batches.append(batch)
    
    # Результаты для каждого потока
    results = {}
    threads = []
    
    def process_url_batch(url_batch: List[str], worker_id: int, delay: int = 0):
        """Обрабатывает батч URL-ов в отдельном потоке"""
        # Отключаем логи selenium-wire для этого потока
        logging.getLogger('seleniumwire').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.storage').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.modifier').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.handler').setLevel(logging.WARNING)
        logging.getLogger('seleniumwire.proxy').setLevel(logging.WARNING)
        
        if delay > 0:
            time.sleep(delay)
        
        thread_print(f"Поток {worker_id}: Начало обработки {len(url_batch)} URL-ов")
        
        batch_results = []
        total_batch_time = 0
        
        for url_index, url in enumerate(url_batch, 1):
            thread_print(f"Поток {worker_id}: URL {url_index}/{len(url_batch)} - {url}")
            start_time = time.time()
            
            try:
                # Проверяем корректность URL
                if not url or "yandex.ru/maps/org/" not in url:
                    thread_print(f"Поток {worker_id}: Некорректный URL: {url}")
                    raise Exception(f"Некорректный URL: {url}")
                
                # Запуск парсинга с повторными попытками при таймауте (profile_path не передаем - используется значение по умолчанию None)
                result = get_reviews_page_with_retry(
                    url=url,
                    device_type=device_type,
                    wait_time=wait_time,
                    max_days_back=max_days_back,
                    max_reviews_limit=max_reviews_limit,
                    use_proxy=use_proxy,
                    max_retries=3  # 3 повторные попытки при таймауте
                )
                
                execution_time = time.time() - start_time
                total_batch_time += execution_time
                
                batch_results.append({
                    "url": url,
                    "result": result,
                    "execution_time": execution_time,
                    "success": True
                })
                
                thread_print(f"Поток {worker_id}: URL {url_index} завершен за {execution_time:.1f}с")
                
            except Exception as e:
                execution_time = time.time() - start_time
                total_batch_time += execution_time
                
                batch_results.append({
                    "url": url,
                    "error": str(e),
                    "execution_time": execution_time,
                    "success": False
                })
                thread_print(f"Поток {worker_id}: URL {url_index} ошибка - {e}")
            
            finally:
                # Пауза между URL-ами в одном потоке для освобождения ресурсов
                if url_index < len(url_batch):
                    time.sleep(delay_between_urls)
        
        # Сохраняем результаты батча
        results[f"worker_{worker_id}"] = {
            "batch_urls": url_batch,
            "batch_results": batch_results,
            "total_batch_time": total_batch_time,
            "urls_processed": len(url_batch),
            "urls_successful": sum(1 for r in batch_results if r.get("success", False)),
            "urls_failed": sum(1 for r in batch_results if not r.get("success", False))
        }
        
        thread_print(f"Поток {worker_id}: Батч завершен за {total_batch_time:.1f}с")
    
    # Запуск потоков с задержками
    start_time = time.time()
    
    for i, batch in enumerate(url_batches):
        delay = i * delay_between_workers  # Задержка между потоками
        thread = Thread(
            target=process_url_batch,
            args=(batch, i + 1, delay)
        )
        threads.append(thread)
        thread.start()
        thread_print(f"🚀 Запущен поток {i + 1}/{len(url_batches)}")
    
    # Мониторинг ресурсов после запуска всех потоков
    thread_print("📊 Мониторинг ресурсов ПОСЛЕ запуска всех потоков:")
    post_start_resources = monitor_system_resources()
    
    # Ожидание завершения всех потоков
    for thread in threads:
        thread.join()
    
    # Мониторинг ресурсов после завершения
    thread_print("📊 Мониторинг ресурсов ПОСЛЕ завершения потоков:")
    final_resources = monitor_system_resources()
    
    total_time = time.time() - start_time
    
    # Подсчет общей статистики
    total_urls_processed = 0
    total_successful = 0
    total_failed = 0
    all_url_results = []
    
    for worker_data in results.values():
        total_urls_processed += worker_data["urls_processed"]
        total_successful += worker_data["urls_successful"]
        total_failed += worker_data["urls_failed"]
        all_url_results.extend(worker_data["batch_results"])
    
    # Подготовка итогового отчета
    summary = {
        "total_urls": len(urls),
        "urls_processed": total_urls_processed,
        "urls_successful": total_successful,
        "urls_failed": total_failed,
        "workers_used": len(url_batches),
        "total_execution_time": total_time,
        "all_results": all_url_results,
        "worker_results": results
    }
    
    # Итоговый отчет
    thread_print(f"ИТОГИ: {total_successful}/{total_urls_processed} URL-ов успешно за {total_time:.1f}с")
    
    return summary


# Функция load_urls_from_file удалена - используем только DEFAULT_URLS

if __name__ == "__main__":
    # ========================================
    # НАСТРОЙКИ ПАРАЛЛЕЛЬНОГО ПАРСЕРА
    # ========================================
    
    # Настройки парсинга
    DEVICE_TYPE = "mobile"              # Тип устройства: "mobile" или "desktop"
    WAIT_TIME = 3                       # Время ожидания в секундах
    MAX_DAYS_BACK = 5                  # Максимальное количество дней назад для первичного парсинга
    MAX_REVIEWS_LIMIT = 2000            # Максимальное количество отзывов для парсинга
    USE_PROXY = True                    # Использовать ли прокси

    # Настройки потоков
    MAX_WORKERS = 20                    # Максимальное количество потоков
    DELAY_BETWEEN_WORKERS = 2           # Задержка между запуском потоков (секунды)
    DELAY_BETWEEN_URLS = 3              # Пауза между URL-ами в одном потоке (секунды)

    # URL-ы для парсинга (можно изменить здесь)
    DEFAULT_URLS = [
        "https://yandex.ru/maps/org/la_bottega_siciliana/61925386633/reviews/",
        "https://yandex.ru/maps/org/novikov/1254142092/reviews/",
        "https://yandex.ru/maps/org/tulskiy_gosudarstvenny_tsirk/1100333178/reviews/", 
        "https://yandex.ru/maps/org/okhotny_ryad/1064113182/reviews/",
        "https://yandex.ru/maps/org/mcdonalds/1076394158/reviews/",
        "https://yandex.ru/maps/org/burger_king/1372282234/reviews/",
        "https://yandex.ru/maps/org/kfc/1139581043/reviews/",
        "https://yandex.ru/maps/org/subway/1054545840/reviews/",
        "https://yandex.ru/maps/org/starbucks/1325748447/reviews/",
        "https://yandex.ru/maps/org/costa_coffee/1209506887/reviews/",
        "https://yandex.ru/maps/org/pizza_hut/1133749027/reviews/",
        "https://yandex.ru/maps/org/dominos_pizza/1139581043/reviews/",
        "https://yandex.ru/maps/org/papa_johns/1054545840/reviews/",
        "https://yandex.ru/maps/org/sushi_wok/1325748447/reviews/",
        "https://yandex.ru/maps/org/yakitoriya/1209506887/reviews/",
        "https://yandex.ru/maps/org/teremok/1133749027/reviews/",
        "https://yandex.ru/maps/org/mu_mu/1139581043/reviews/",
        "https://yandex.ru/maps/org/shokoladnitsa/1054545840/reviews/",
        "https://yandex.ru/maps/org/coffee_house/1325748447/reviews/",
        "https://yandex.ru/maps/org/kruzhka/1209506887/reviews/"
    ]
    
    # Инициализация с очисткой старых профилей
    initialize_profiles_cleanup()
    
    # Используем URL-ы по умолчанию из настроек
    test_urls = DEFAULT_URLS
    
    # Количество потоков (можно изменить здесь)
    workers_count = min(MAX_WORKERS, len(test_urls))  # Используем MAX_WORKERS или количество URL-ов
    
    # Запуск парсинга
    thread_print("Запуск параллельного парсера...")
    thread_print(f"Настройки: {DEVICE_TYPE}, {MAX_DAYS_BACK} дней, макс. {MAX_REVIEWS_LIMIT} отзывов")
    results = parse_urls(
        test_urls, 
        workers_count,
        device_type=DEVICE_TYPE,
        wait_time=WAIT_TIME,
        max_days_back=MAX_DAYS_BACK,
        max_reviews_limit=MAX_REVIEWS_LIMIT,
        use_proxy=USE_PROXY,
        max_workers=MAX_WORKERS,
        delay_between_workers=DELAY_BETWEEN_WORKERS,
        delay_between_urls=DELAY_BETWEEN_URLS
    )
    
    # Вывод дополнительной статистики
    if results.get("all_results"):
        thread_print("\n" + "=" * 60)
        thread_print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")
        thread_print("=" * 60)
        thread_print(f"Всего URL-ов: {results['total_urls']}")
        thread_print(f"Обработано: {results['urls_processed']}")
        thread_print(f"Успешно: {results['urls_successful']}")
        thread_print(f"Ошибок: {results['urls_failed']}")
        thread_print(f"Потоков: {results['workers_used']}")
        
        # Показываем результаты по URL-ам
        for i, result in enumerate(results["all_results"], 1):
            thread_print(f"\n📋 URL #{i}:")
            thread_print(f"  🔗 Адрес: {result['url']}")
            thread_print(f"  📊 Статус: {'✅ УСПЕХ' if result.get('success') else '❌ ОШИБКА'}")
            thread_print(f"  ⏱️ Время: {result['execution_time']:.1f} секунд")
            if not result.get("success"):
                thread_print(f"  ❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
        # Показываем результаты по потокам
        thread_print(f"\n" + "=" * 60)
        thread_print("СТАТИСТИКА ПО ПОТОКАМ")
        thread_print("=" * 60)
        
        for worker_id, worker_data in results["worker_results"].items():
            thread_print(f"\n🔧 {worker_id.upper()}:")
            thread_print(f"  📋 URL-ов в батче: {worker_data['urls_processed']}")
            thread_print(f"  ✅ Успешно: {worker_data['urls_successful']}")
            thread_print(f"  ❌ Ошибок: {worker_data['urls_failed']}")
            thread_print(f"  ⏱️ Общее время: {worker_data['total_batch_time']:.1f} секунд") 
    
    # Финальная очистка всех профилей
    cleanup_all_profiles() 