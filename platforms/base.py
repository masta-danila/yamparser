"""
Базовый класс для обработчиков платформ отзывов.
Все платформы (Яндекс, Google, 2GIS, Zoon) должны реализовать этот интерфейс.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BasePlatformHandler(ABC):
    """Абстрактный базовый класс для парсеров отзывов с разных платформ."""

    @staticmethod
    @abstractmethod
    def can_handle(url: str) -> bool:
        """
        Проверяет, подходит ли URL для этой платформы.

        Args:
            url: URL страницы с отзывами

        Returns:
            True если платформа может обработать этот URL
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Название платформы для логов."""
        pass

    @abstractmethod
    def get_reviews(
        self,
        url: str,
        card_id: Optional[str] = None,
        device_type: str = "mobile",
        max_days_back: int = 30,
        max_reviews_limit: int = 100,
        use_proxy: bool = True,
        max_retries: int = 2,  # 3 попытки всего (1 начальная + 2 повтора)
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Парсит отзывы со страницы.

        Returns:
            {
                "success": bool,
                "reviews": [{"author": str, "text": str, "date": str, "rating": str}, ...],
                "reviews_found": int,
                "error": str | None,
                "url": str,
                "card_id": str,
                ...
            }
        """
        pass
