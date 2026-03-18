"""
Прокрутка и подгрузка отзывов на Zoon.ru.
Страница скроллится по window, подгрузка — по кнопке «Показать еще».
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from thread_logger import thread_print

# Кнопка «Показать еще» — только внутри блока отзывов (не путать с кнопкой «Позвонить»)
SHOW_MORE_SELECTORS = [
    "div.comments-next a.js-show-more",
    "div.js-show-more-box a[data-uitest='show-more-comments-button']",
    "#reviews a.js-show-more",
]
# Контейнер с кнопкой (может скрываться при загрузке)
SHOW_MORE_BOX = "div.js-show-more-box"
# Лоадер при подгрузке
LOADER_SELECTOR = "div.js-loader"
# Список отзывов
REVIEW_LIST_SELECTOR = "ul.js-feedbacks-new.js-comment-list"
REVIEW_ITEM_SELECTOR = "li.comment-item.js-comment"


def scroll_zoon_reviews(driver, max_attempts=20):
    """
    Прокрутка страницы Zoon и нажатие «Показать еще» для подгрузки отзывов.
    Страница скроллится по window (document), подгрузка — по кнопке.
    """
    no_new_count = 0
    last_count = 0

    for attempt in range(max_attempts):
        # 1. Прокрутка window вниз — чтобы кнопка «Показать еще» была видна
        try:
            driver.execute_script(
                "window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));"
            )
            time.sleep(0.5)
        except Exception:
            pass

        # 2. Ищем и нажимаем кнопку «Показать еще»
        # Кнопка может быть перекрыта фиксированной панелью внизу (call-btn-panel)
        clicked = False
        load_more = None
        for sel in SHOW_MORE_SELECTORS:
            try:
                load_more = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except Exception:
                continue
        if load_more:
            try:
                # Скрыть панель «Позвонить» — иначе клик может попасть на неё
                driver.execute_script("""
                    var p = document.getElementById('serviceCallBtnPanel') || document.querySelector('.call-btn-panel');
                    if (p) p.style.display = 'none';
                """)
                time.sleep(0.2)
                # Прокрутить кнопку в центр экрана
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", load_more)
                time.sleep(0.3)
                # Только JS-клик — не ActionChains, чтобы не попасть по другому элементу
                driver.execute_script("arguments[0].click();", load_more)
                clicked = True
                thread_print("Прокрутка Zoon: нажата кнопка «Показать еще»")
                time.sleep(2)  # ждём подгрузку
            except Exception as e:
                thread_print(f"Прокрутка Zoon: клик не сработал: {e}")
            finally:
                driver.execute_script("""
                    var p = document.getElementById('serviceCallBtnPanel') || document.querySelector('.call-btn-panel');
                    if (p) p.style.display = '';
                """)

        # 3. Дополнительная прокрутка window (на случай lazy-load без кнопки)
        try:
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.4)
        except Exception:
            pass

        # 4. Считаем отзывы
        try:
            items = driver.find_elements(By.CSS_SELECTOR, REVIEW_ITEM_SELECTOR)
            count = len(items)
        except Exception:
            count = 0

        if count == last_count:
            no_new_count += 1
            if no_new_count >= 3:
                thread_print("Прокрутка Zoon: новых отзывов нет, остановка")
                break
        else:
            no_new_count = 0
            thread_print(f"Прокрутка Zoon: найдено {count} отзывов")

        last_count = count

        # Если кнопки нет и новых отзывов не прибавилось — выходим
        if not clicked and no_new_count >= 2:
            thread_print("Прокрутка Zoon: кнопка «Показать еще» не найдена, остановка")
            break

        time.sleep(0.5)

    return last_count


def scroll_zoon_one_batch(driver):
    """
    Один цикл: прокрутка + клик «Показать еще».
    Возвращает True если клик был, False если кнопки нет.
    """
    try:
        driver.execute_script(
            "window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));"
        )
        time.sleep(0.5)
    except Exception:
        pass

    clicked = False
    try:
        for sel in SHOW_MORE_SELECTORS:
            try:
                load_more = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                driver.execute_script("""
                    var p = document.getElementById('serviceCallBtnPanel') || document.querySelector('.call-btn-panel');
                    if (p) p.style.display = 'none';
                """)
                time.sleep(0.2)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", load_more)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", load_more)
                clicked = True
                time.sleep(2)
                break
            except Exception:
                continue
    finally:
        driver.execute_script("""
            var p = document.getElementById('serviceCallBtnPanel') || document.querySelector('.call-btn-panel');
            if (p) p.style.display = '';
        """)

    try:
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(0.3)
    except Exception:
        pass
    return clicked
