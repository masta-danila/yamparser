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
        max_retries: int = 3,
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Полный цикл: открывает URL Zoon, закрывает попапы, переходит на «Отзывы»,
        прокручивает и подгружает отзывы, извлекает их.
        """
        from driver_manager import setup_driver
        from thread_logger import thread_print

        proxy_manager = None
        if use_proxy:
            try:
                from proxy_manager import ProxyManagerSeleniumWire
                proxy_manager = ProxyManagerSeleniumWire()
            except Exception as e:
                thread_print(f"❌ Прокси: {e}")

        driver = None
        try:
            thread_print(f"🚀 Открываем страницу Zoon: {url}")
            driver = setup_driver(device_type, proxy_manager, None)
            if not driver:
                return {
                    "success": False,
                    "reviews": [],
                    "reviews_found": 0,
                    "error": "Не удалось запустить браузер",
                    "url": url,
                    "card_id": card_id,
                }

            driver.set_page_load_timeout(30)
            driver.get(url)
            thread_print("✅ Страница Zoon загружена!")
            time.sleep(2)

            try:
                from popup_handler import close_zoon_age_popup, close_zoon_cookie_popup, click_zoon_reviews_tab
                close_zoon_age_popup(driver)
                time.sleep(1)
                close_zoon_cookie_popup(driver)
                time.sleep(1)
                click_zoon_reviews_tab(driver)
            except Exception as e:
                thread_print(f"⚠️ Попап/вкладка Zoon: {e}")

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

            return {
                "success": True,
                "reviews": reviews_data,
                "reviews_found": len(reviews_data),
                "error": None,
                "url": url,
                "card_id": card_id,
            }

        except Exception as e:
            thread_print(f"❌ Ошибка Zoon: {e}")
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            return {
                "success": False,
                "reviews": [],
                "reviews_found": 0,
                "error": str(e),
                "url": url,
                "card_id": card_id,
            }
