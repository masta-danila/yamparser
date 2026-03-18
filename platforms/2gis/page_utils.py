"""
Утилиты для работы со страницей 2GIS (навигация, клики).
"""

import time
from selenium.webdriver.common.by import By

from thread_logger import thread_print


def click_reviews_tab(driver):
    """
    Кликает по вкладке «Отзывы» на странице 2GIS.
    """
    try:
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
        return False
    except Exception as e:
        thread_print(f"⚠️ Ошибка клика по вкладке Отзывы 2GIS: {e}")
        return False
