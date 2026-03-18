"""
Роутер: определяет платформу по URL и возвращает соответствующий обработчик.
"""

from typing import Optional

from .base import BasePlatformHandler


def get_handler_for_url(url: str) -> Optional[BasePlatformHandler]:
    """
    Определяет платформу по URL и возвращает обработчик.

    Args:
        url: URL страницы с отзывами

    Returns:
        Обработчик платформы или None если платформа не поддерживается
    """
    from .yandex import YandexMapsHandler
    # 2gis — имя папки с цифрой, импорт через importlib
    import importlib
    gis2 = importlib.import_module("platforms.2gis")
    TwoGisHandler = gis2.TwoGisHandler

    handlers = [YandexMapsHandler, TwoGisHandler]

    for Handler in handlers:
        if Handler.can_handle(url):
            return Handler()

    return None
