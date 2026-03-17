"""
Модуль платформ для парсинга отзывов.
Каждая платформа (Яндекс, Google, 2GIS, Zoon) реализует единый интерфейс.
"""

from .base import BasePlatformHandler
from .router import get_handler_for_url

__all__ = ['BasePlatformHandler', 'get_handler_for_url']
