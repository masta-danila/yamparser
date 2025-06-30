import sys
import os
import time
import logging
from threading import Thread, Lock
from typing import List, Dict, Any
from reviews_parser import get_reviews_page
from driver_manager import get_driver_creation_lock

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
        
        logger.info(f"Поток {worker_id}: Начало обработки {len(url_batch)} URL-ов")
        
        batch_results = []
        total_batch_time = 0
        
        for url_index, url in enumerate(url_batch, 1):
            logger.info(f"Поток {worker_id}: URL {url_index}/{len(url_batch)} - {url}")
            start_time = time.time()
            
            try:
                # Проверяем корректность URL
                if not url or "yandex.ru/maps/org/" not in url:
                    logger.error(f"Поток {worker_id}: Некорректный URL: {url}")
                    raise Exception(f"Некорректный URL: {url}")
                
                # Запуск парсинга (profile_path не передаем - используется значение по умолчанию None)
                result = get_reviews_page(
                    url=url,
                    device_type=device_type,
                    wait_time=wait_time,
                    max_days_back=max_days_back,
                    max_reviews_limit=max_reviews_limit,
                    use_proxy=use_proxy
                )
                
                execution_time = time.time() - start_time
                total_batch_time += execution_time
                
                batch_results.append({
                    "url": url,
                    "result": result,
                    "execution_time": execution_time,
                    "success": True
                })
                
                logger.info(f"Поток {worker_id}: URL {url_index} завершен за {execution_time:.1f}с")
                
            except Exception as e:
                execution_time = time.time() - start_time
                total_batch_time += execution_time
                
                batch_results.append({
                    "url": url,
                    "error": str(e),
                    "execution_time": execution_time,
                    "success": False
                })
                logger.error(f"Поток {worker_id}: URL {url_index} ошибка - {e}")
            
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
        
        logger.info(f"Поток {worker_id}: Батч завершен за {total_batch_time:.1f}с")
    
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
    
    # Ожидание завершения всех потоков
    for thread in threads:
        thread.join()
    
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
    logger.info(f"ИТОГИ: {total_successful}/{total_urls_processed} URL-ов успешно за {total_time:.1f}с")
    
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
    MAX_WORKERS = 5                     # Максимальное количество потоков
    DELAY_BETWEEN_WORKERS = 2           # Задержка между запуском потоков (секунды)
    DELAY_BETWEEN_URLS = 3              # Пауза между URL-ами в одном потоке (секунды)

    # URL-ы для парсинга (можно изменить здесь)
    DEFAULT_URLS = [
        "https://yandex.ru/maps/org/la_bottega_siciliana/61925386633/reviews/",
        "https://yandex.ru/maps/org/novikov/1254142092/reviews/",
        "https://yandex.ru/maps/org/tulskiy_gosudarstvenny_tsirk/1100333178/reviews/", 
        "https://yandex.ru/maps/org/okhotny_ryad/1064113182/reviews/"
    ]
    
    # Используем URL-ы по умолчанию из настроек
    test_urls = DEFAULT_URLS
    
    # Количество потоков (можно изменить здесь)
    workers_count = min(MAX_WORKERS, len(test_urls))  # Используем MAX_WORKERS или количество URL-ов
    
    # Запуск парсинга
    logger.info("Запуск параллельного парсера...")
    logger.info(f"Настройки: {DEVICE_TYPE}, {MAX_DAYS_BACK} дней, макс. {MAX_REVIEWS_LIMIT} отзывов")
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
        print("\n" + "=" * 60)
        print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")
        print("=" * 60)
        print(f"Всего URL-ов: {results['total_urls']}")
        print(f"Обработано: {results['urls_processed']}")
        print(f"Успешно: {results['urls_successful']}")
        print(f"Ошибок: {results['urls_failed']}")
        print(f"Потоков: {results['workers_used']}")
        
        # Показываем результаты по URL-ам
        for i, result in enumerate(results["all_results"], 1):
            print(f"\n📋 URL #{i}:")
            print(f"  🔗 Адрес: {result['url']}")
            print(f"  📊 Статус: {'✅ УСПЕХ' if result.get('success') else '❌ ОШИБКА'}")
            print(f"  ⏱️ Время: {result['execution_time']:.1f} секунд")
            if not result.get("success"):
                print(f"  ❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
        # Показываем результаты по потокам
        print(f"\n" + "=" * 60)
        print("СТАТИСТИКА ПО ПОТОКАМ")
        print("=" * 60)
        
        for worker_id, worker_data in results["worker_results"].items():
            print(f"\n🔧 {worker_id.upper()}:")
            print(f"  📋 URL-ов в батче: {worker_data['urls_processed']}")
            print(f"  ✅ Успешно: {worker_data['urls_successful']}")
            print(f"  ❌ Ошибок: {worker_data['urls_failed']}")
            print(f"  ⏱️ Общее время: {worker_data['total_batch_time']:.1f} секунд") 