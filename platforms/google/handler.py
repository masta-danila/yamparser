"""
Обработчик отзывов Google Maps.
Пока только открывает страницу для инспектирования.
"""

import time
from typing import Dict, Any, Optional

from ..base import BasePlatformHandler


class GoogleMapsHandler(BasePlatformHandler):
    """Парсер отзывов с Google Maps (в разработке)."""

    @staticmethod
    def can_handle(url: str) -> bool:
        """Проверяет, является ли URL страницей Google Maps."""
        if not url:
            return False
        url_lower = url.lower().strip()
        return (
            "maps.app.goo.gl" in url_lower
            or "goo.gl/maps" in url_lower
            or "google.com/maps" in url_lower
        )

    @property
    def name(self) -> str:
        return "Google Maps"

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
        Открывает URL Google Maps и останавливается для инспектирования.
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
            thread_print(f"🚀 Открываем страницу Google Maps: {url}")
            # Google Maps — только desktop, мобильная версия проблемная
            driver = setup_driver("desktop", proxy_manager, None)
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
            thread_print("✅ Страница Google Maps загружена!")

            time.sleep(2)
            try:
                from popup_handler import close_google_maps_app_popup
                close_google_maps_app_popup(driver)
            except Exception as e:
                thread_print(f"⚠️ Попап Google Maps: {e}")
            time.sleep(1)

            thread_print("⏸️  Браузер открыт — инспектируйте страницу. Нажмите Enter для закрытия...")
            input()

        except Exception as e:
            thread_print(f"❌ Ошибка: {e}")
            return {
                "success": False,
                "reviews": [],
                "reviews_found": 0,
                "error": str(e),
                "url": url,
                "card_id": card_id,
            }
        finally:
            if driver:
                driver.quit()

        return {
            "success": True,
            "reviews": [],
            "reviews_found": 0,
            "error": None,
            "url": url,
            "card_id": card_id,
        }
