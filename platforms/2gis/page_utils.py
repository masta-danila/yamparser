"""
Утилиты для работы со страницей 2GIS (навигация, клики).
"""

import time
from selenium.webdriver.common.by import By

from thread_logger import thread_print


def has_reviews_tab(driver):
    """Проверяет, есть ли на странице вкладка «Отзывы»."""
    selectors = [
        (By.XPATH, "//a[contains(., 'Отзывы') and contains(@href, '/tab/reviews')]"),
        (By.CSS_SELECTOR, "a._2lcm958[href*='/tab/reviews']"),
        (By.XPATH, "//a[contains(@href, '/tab/reviews')]"),
    ]
    for by, selector in selectors:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    return True
        except Exception:
            pass
    return False


def has_info_tab_only(driver):
    """
    Проверяет, есть ли блок с вкладкой «Инфо» без вкладки «Отзывы».
    Это означает, что на карточке нет отзывов (пустая карточка).
    """
    try:
        # Блок с вкладками: div с ссылкой на /tab/info
        info_tab = driver.find_elements(By.XPATH, "//a[contains(@href, '/tab/info')]")
        if info_tab:
            # Есть вкладка Инфо, но нет вкладки Отзывы — значит отзывов нет
            return not has_reviews_tab(driver)
    except Exception:
        pass
    return False


def click_reviews_tab(driver):
    """
    Кликает по вкладке «Отзывы» на странице 2GIS.
    Вызывает RuntimeError, если элемент не найден (критичный элемент, не попап).
    """
    selectors = [
        (By.XPATH, "//a[contains(., 'Отзывы') and contains(@href, '/tab/reviews')]"),
        (By.CSS_SELECTOR, "a._2lcm958[href*='/tab/reviews']"),
        (By.XPATH, "//a[contains(@href, '/tab/reviews')]"),
    ]
    for by, selector in selectors:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    thread_print("✅ Вкладка «Отзывы» открыта")
                    time.sleep(2)
                    return True
        except Exception:
            pass
    raise RuntimeError(
        "Вкладка «Отзывы» не найдена на странице 2GIS. "
        "Проверьте структуру страницы или доступность сайта."
    )
