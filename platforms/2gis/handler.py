"""
Обработчик отзывов 2GIS.
Открывает страницу, закрывает попапы, переходит на вкладку «Отзывы» и парсит отзывы.
"""

import time
from typing import Dict, Any, Optional

from ..base import BasePlatformHandler


class TwoGisHandler(BasePlatformHandler):
    """Парсер отзывов с 2GIS (в разработке)."""

    @staticmethod
    def can_handle(url: str) -> bool:
        """Проверяет, является ли URL страницей 2GIS."""
        if not url:
            return False
        url_lower = url.lower().strip()
        return '2gis.ru' in url_lower or '2gis.com' in url_lower

    @property
    def name(self) -> str:
        return "2GIS"

    def get_reviews(
        self,
        url: str,
        card_id: Optional[str] = None,
        device_type: str = "mobile",
        max_days_back: int = 30,
        max_reviews_limit: int = 100,
        use_proxy: bool = True,
        max_retries: int = 3,
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Открывает URL 2GIS, закрывает попапы, кликает «Отзывы» и извлекает отзывы.
        """
        from driver_manager import setup_driver, initialize_profiles_cleanup, cleanup_all_profiles
        from thread_logger import thread_print

        proxy_manager = None
        if use_proxy:
            try:
                from proxy_manager import ProxyManagerSeleniumWire
                proxy_manager = ProxyManagerSeleniumWire()
                stats = proxy_manager.get_stats()
                thread_print(f"✅ Доступно прокси: {stats['total_proxies']}")
            except Exception as e:
                thread_print(f"❌ Ошибка инициализации прокси: {e}")
                return {
                    "success": False,
                    "reviews": [],
                    "reviews_found": 0,
                    "error": f"Прокси недоступны: {e}",
                    "url": url,
                    "card_id": card_id,
                }

        if not proxy_manager:
            return {
                "success": False,
                "reviews": [],
                "reviews_found": 0,
                "error": "Прокси обязательны (настройте proxy.txt)",
                "url": url,
                "card_id": card_id,
            }

        initialize_profiles_cleanup()
        last_error = None

        # Для 2GIS можно использовать desktop, если mobile не скроллится
        try:
            from config import TWO_GIS_DEVICE_TYPE
            effective_device = TWO_GIS_DEVICE_TYPE
        except ImportError:
            effective_device = device_type
        if effective_device != device_type:
            thread_print(f"📱 2GIS: используем {effective_device} (config.TWO_GIS_DEVICE_TYPE)")

        for attempt in range(max_retries + 1):
            driver = None
            try:
                if attempt > 0:
                    thread_print(f"🔄 ПОВТОРНАЯ ПОПЫТКА {attempt}/{max_retries} с новым браузером и прокси...")
                    time.sleep(2)
                else:
                    thread_print(f"🚀 Открываем страницу 2GIS: {url}")

                driver = setup_driver(effective_device, proxy_manager, None)

                if not driver:
                    last_error = "Не удалось запустить браузер (все прокси недоступны)"
                    continue

                driver.set_page_load_timeout(30)
                driver.get(url)
                thread_print("✅ Страница 2GIS загружена!")

                time.sleep(2)  # Даём попапу отрендериться

                # Закрываем попап «Выберите где продолжить» — кнопка «Остаться»
                try:
                    from popup_handler import close_2gis_app_popup
                    close_2gis_app_popup(driver)
                except Exception as e:
                    thread_print(f"⚠️ Попап 2GIS: {e}")

                time.sleep(1)

                # Закрываем попап cookies «Мы используем cookies»
                try:
                    from popup_handler import close_2gis_cookie_popup
                    close_2gis_cookie_popup(driver)
                except Exception as e:
                    thread_print(f"⚠️ Попап cookies 2GIS: {e}")

                time.sleep(1)

                # Кликаем по вкладке «Отзывы»
                try:
                    from .page_utils import click_reviews_tab
                    click_reviews_tab(driver)
                except Exception as e:
                    thread_print(f"⚠️ Вкладка Отзывы 2GIS: {e}")

                time.sleep(2)  # Даём отзывам загрузиться

                # Извлекаем отзывы (прокрутка, парсинг, фильтр по дате)
                from .review_extractor import extract_reviews as extract_2gis_reviews
                reviews_data = extract_2gis_reviews(
                    driver,
                    max_days_back=max_days_back,
                    max_reviews_limit=max_reviews_limit,
                    scroll_to_load=True,
                    target_date=target_date,
                )

                if driver:
                    driver.quit()
                    driver = None
                cleanup_all_profiles()

                return {
                    "success": True,
                    "reviews": reviews_data,
                    "reviews_found": len(reviews_data),
                    "url": url,
                    "card_id": card_id,
                }

            except Exception as e:
                last_error = str(e)
                thread_print(f"❌ Ошибка 2GIS (попытка {attempt + 1}/{max_retries + 1}): {e}")
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = None
                if attempt < max_retries:
                    thread_print("🔄 Повторная попытка с новым браузером...")
                continue

        cleanup_all_profiles()
        return {
            "success": False,
            "reviews": [],
            "reviews_found": 0,
            "error": f"Все {max_retries + 1} попытки неуспешны. Последняя ошибка: {last_error}",
            "url": url,
            "card_id": card_id,
        }
