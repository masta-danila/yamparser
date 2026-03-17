"""
Обработчик отзывов Яндекс.Карт.
Оборачивает reviews_parser.get_reviews_page_with_retry.
"""

from typing import Dict, Any, Optional

from ..base import BasePlatformHandler


class YandexMapsHandler(BasePlatformHandler):
    """Парсер отзывов с Яндекс.Карт."""

    @staticmethod
    def can_handle(url: str) -> bool:
        """Проверяет, является ли URL страницей отзывов Яндекс.Карт."""
        if not url:
            return False
        url_lower = url.lower().strip()
        return (
            'yandex.ru/maps' in url_lower or
            'yandex.com/maps' in url_lower
        ) and ('/reviews' in url_lower or '/org/' in url_lower)

    @property
    def name(self) -> str:
        return "Яндекс.Карты"

    def get_reviews(
        self,
        url: str,
        card_id: Optional[str] = None,
        device_type: str = "mobile",
        max_days_back: int = 30,
        max_reviews_limit: int = 100,
        use_proxy: bool = True,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Парсит отзывы с Яндекс.Карт через get_reviews_page_with_retry."""
        from reviews_parser import get_reviews_page_with_retry

        result = get_reviews_page_with_retry(
            url=url,
            device_type=device_type,
            wait_time=3,
            max_days_back=max_days_back,
            max_reviews_limit=max_reviews_limit,
            use_proxy=use_proxy,
            max_retries=max_retries,
            card_id=card_id,
        )

        return result or {
            "success": False,
            "reviews": [],
            "reviews_found": 0,
            "error": "Парсер вернул пустой результат",
            "url": url,
            "card_id": card_id,
        }
