"""
Обработчик отзывов Zoon.ru.
Полный цикл: открытие, попапы, вкладка «Отзывы», прокрутка, извлечение.
"""

import time
from typing import Dict, Any, Optional

from ..base import BasePlatformHandler


class ZoonHandler(BasePlatformHandler):
    """Парсер отзывов с Zoon.ru."""

    @staticmethod
    def can_handle(url: str) -> bool:
        """Проверяет, является ли URL страницей Zoon.ru."""
        if not url:
            return False
        url_lower = url.lower().strip()
        return "zoon.ru" in url_lower

    @property
    def name(self) -> str:
        return "Zoon"

    def get_reviews(
        self,
        url: str,
        card_id: Optional[str] = None,
        device_type: str = "mobile",
        max_days_back: int = 30,
        max_reviews_limit: int = 100,
        use_proxy: bool = True,
        max_retries: int = 2,
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Полный цикл: открывает URL Zoon, закрывает попапы, переходит на «Отзывы»,
        прокручивает и подгружает отзывы, извлекает их.
        """
        from driver_manager import setup_driver, initialize_profiles_cleanup, cleanup_all_profiles
        from thread_logger import thread_print

        proxy_manager = None
        if use_proxy:
            try:
                from proxy_manager import ProxyManagerSeleniumWire
                proxy_manager = ProxyManagerSeleniumWire()
            except Exception as e:
                thread_print(f"❌ Прокси: {e}")

        initialize_profiles_cleanup()
        last_error = None

        for attempt in range(max_retries + 1):
            driver = None
            try:
                if attempt > 0:
                    thread_print(f"🔄 ПОВТОРНАЯ ПОПЫТКА {attempt}/{max_retries} с новым браузером и прокси...")
                    time.sleep(2)
                else:
                    thread_print(f"🚀 Открываем страницу Zoon: {url}")

                driver = setup_driver(device_type, proxy_manager, None)
                if not driver:
                    last_error = "Не удалось запустить браузер"
                    continue

                driver.set_page_load_timeout(30)
                driver.get(url)
                thread_print("✅ Страница Zoon загружена!")
                time.sleep(2)

                # Попапы — не критичны, ошибки игнорируем
                try:
                    from popup_handler import close_zoon_age_popup, close_zoon_cookie_popup
                    close_zoon_age_popup(driver)
                    time.sleep(1)
                    close_zoon_cookie_popup(driver)
                    time.sleep(1)
                except Exception as e:
                    thread_print(f"⚠️ Попап Zoon: {e}")

                # Вкладка «Отзывы» — критичный элемент, при отсутствии выбросит ошибку
                from popup_handler import click_zoon_reviews_tab
                click_zoon_reviews_tab(driver)
                time.sleep(2)

                from .review_extractor import extract_reviews as extract_zoon_reviews
                reviews_data = extract_zoon_reviews(
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

                if not reviews_data:
                    return {
                        "success": False,
                        "reviews": [],
                        "reviews_found": 0,
                        "error": "Отзывы не найдены на странице Zoon. Проверьте структуру страницы или наличие отзывов.",
                        "url": url,
                        "card_id": card_id,
                    }

                return {
                    "success": True,
                    "reviews": reviews_data,
                    "reviews_found": len(reviews_data),
                    "error": None,
                    "url": url,
                    "card_id": card_id,
                }

            except Exception as e:
                last_error = str(e)
                thread_print(f"❌ Ошибка Zoon (попытка {attempt + 1}/{max_retries + 1}): {e}")
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
