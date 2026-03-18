"""
Извлечение отзывов со страницы 2GIS.
"""

import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

from thread_logger import thread_print

try:
    from reviews_parser import parse_review_date
except ImportError:
    def parse_review_date(s):
        return s


REVIEW_CONTAINER = "div._1k5soqfl"
AUTHOR_SELECTOR = "span._16s5yj36"
DATE_SELECTOR = "div._a5f6uz"
# Длинные отзывы: a._1wlx08h, короткие: a._1msln3t — оба внутри div._49x36f
TEXT_SELECTOR = "div._49x36f a"
RATING_STARS = "svg[fill='#ffb81c']"


def _extract_single_review(container):
    try:
        review_data = {"author": "Аноним", "date": "", "rating": None, "text": ""}

        try:
            text_el = container.find_element(By.CSS_SELECTOR, TEXT_SELECTOR)
            review_data["text"] = (text_el.text or "").strip()
        except Exception:
            pass

        if not review_data["text"]:
            return None

        try:
            author_el = container.find_element(By.CSS_SELECTOR, AUTHOR_SELECTOR)
            author = author_el.get_attribute("title") or author_el.text or ""
            if author.strip():
                review_data["author"] = author.strip()
        except Exception:
            pass

        try:
            date_el = container.find_element(By.CSS_SELECTOR, DATE_SELECTOR)
            review_data["date"] = (date_el.text or "").strip()
        except Exception:
            pass

        try:
            stars = container.find_elements(By.CSS_SELECTOR, RATING_STARS)
            if stars:
                review_data["rating"] = len(stars)
        except Exception:
            pass

        return review_data
    except Exception:
        return None


# 2GIS mobile: контейнер прокрутки с data-scroll="true" (div._68wtdv)
SCROLL_CONTAINER_SELECTOR = "[data-scroll='true']"


def _find_scroll_target(driver):
    """Находит scrollable-контейнер 2GIS. Приоритет: [data-scroll='true'] -> родитель отзыва."""
    scroll_target = None
    # 1. Явный контейнер 2GIS (из HTML: div._68wtdv с data-scroll="true")
    try:
        els = driver.find_elements(By.CSS_SELECTOR, SCROLL_CONTAINER_SELECTOR)
        for el in els:
            try:
                sh = driver.execute_script("return arguments[0].scrollHeight", el)
                ch = driver.execute_script("return arguments[0].clientHeight", el)
                if sh > ch + 20:
                    scroll_target = el
                    break
            except Exception:
                continue
        if scroll_target:
            return scroll_target
    except Exception:
        pass
    # 2. Родитель первого отзыва
    try:
        first_review = driver.find_element(By.CSS_SELECTOR, REVIEW_CONTAINER)
    except Exception:
        try:
            first_review = driver.find_element(By.XPATH, "//div[.//div[contains(@class,'_49x36f')]]")
        except Exception:
            first_review = None
    if first_review:
        parent = first_review
        for _ in range(15):
            try:
                parent = parent.find_element(By.XPATH, "..")
                sh = driver.execute_script("return arguments[0].scrollHeight", parent)
                ch = driver.execute_script("return arguments[0].clientHeight", parent)
                if sh > ch + 50:
                    scroll_target = parent
                    break
            except Exception:
                break
    if scroll_target:
        return scroll_target
    # 3. Общие селекторы
    for selector in ["[class*='scroll']", "main", "[role='main']"]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                try:
                    sh = driver.execute_script("return arguments[0].scrollHeight", el)
                    ch = driver.execute_script("return arguments[0].clientHeight", el)
                    if sh > ch:
                        return el
                except Exception:
                    continue
        except Exception:
            continue
    return None


def _scroll_container(driver, scroll_target, step=500):
    """Прокрутка контейнера: scrollTop, пошаговый скролл, touch-события."""
    if not scroll_target:
        return
    try:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_target)
        driver.execute_script("arguments[0].scrollTop += arguments[1]", scroll_target, step)
        time.sleep(0.5)
        # Пошаговый скролл для lazy-load
        driver.execute_script("""
            var el = arguments[0], step = 600;
            for (var i = 0; i < 5; i++) {
                el.scrollTop += step;
                if (el.scrollTop >= el.scrollHeight - el.clientHeight) break;
            }
            el.scrollTop = el.scrollHeight;
        """, scroll_target)
        time.sleep(0.6)
    except Exception:
        pass
    # Touch-события для мобильной версии (2GIS может реагировать только на touch)
    try:
        driver.execute_script("""
            var el = arguments[0];
            var rect = el.getBoundingClientRect();
            var cx = rect.left + rect.width/2;
            var y1 = rect.top + rect.height - 50;
            var y2 = y1 - 400;
            var touch = {clientX: cx, clientY: y1, identifier: 1};
            var touchStart = new TouchEvent('touchstart', {touches: [touch], changedTouches: [touch]});
            touch.clientY = y2;
            var touchMove = new TouchEvent('touchmove', {touches: [touch], changedTouches: [touch]});
            var touchEnd = new TouchEvent('touchend', {touches: [], changedTouches: [touch]});
            el.dispatchEvent(touchStart);
            el.dispatchEvent(touchMove);
            el.dispatchEvent(touchEnd);
        """, scroll_target)
        time.sleep(0.5)
    except Exception:
        pass


def _scroll_to_load_more(driver, max_attempts=25):
    """
    Прокрутка для подгрузки отзывов 2GIS.
    На мобильной версии 2GIS прокрутка идёт в div[data-scroll="true"], а не в window.
    """
    from selenium.webdriver.common.keys import Keys

    no_new_count = 0
    last_count = 0
    scroll_target_logged = False

    for attempt in range(max_attempts):
        scroll_target = _find_scroll_target(driver)

        if not scroll_target_logged:
            if scroll_target:
                thread_print("Прокрутка 2GIS: найден scrollable-контейнер")
            else:
                thread_print("Прокрутка 2GIS: scrollable-контейнер не найден, скролл только window")
            scroll_target_logged = True

        # 1. Кнопка «Загрузить ещё» — если есть, нажать до прокрутки
        try:
            load_more = driver.find_element(By.CSS_SELECTOR, "button._kuel4no")
            if load_more.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", load_more)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", load_more)
                thread_print("Прокрутка 2GIS: нажата кнопка «Загрузить ещё»")
                time.sleep(1.5)
        except Exception:
            pass

        # 2. Прокрутка контейнера (приоритет для 2GIS mobile)
        _scroll_container(driver, scroll_target, step=600)

        # 3. scrollIntoView последнего отзыва — триггер lazy-load
        try:
            containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
            if not containers:
                containers = driver.find_elements(By.XPATH, "//div[.//div[contains(@class,'_49x36f')]]")
            if containers:
                last_review = containers[-1]
                driver.execute_script("arguments[0].scrollIntoView({block: 'end', behavior: 'auto'});", last_review)
                time.sleep(0.8)
                # Если есть scroll_target — прокрутка внутри него до последнего отзыва
                if scroll_target:
                    driver.execute_script("""
                        var el = arguments[0], last = arguments[1];
                        var rect = last.getBoundingClientRect();
                        var elRect = el.getBoundingClientRect();
                        var offset = rect.top - elRect.top + el.scrollTop;
                        el.scrollTop = Math.min(offset + 200, el.scrollHeight - el.clientHeight);
                    """, scroll_target, last_review)
                    time.sleep(0.5)
        except Exception:
            pass

        # 4. Прокрутка window (fallback на desktop)
        driver.execute_script("window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));")
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.4)

        # 5. ActionChains scroll
        if scroll_target:
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
                origin = ScrollOrigin.from_element(scroll_target)
                ActionChains(driver).scroll_from_origin(origin, 0, 600).perform()
                time.sleep(0.4)
            except Exception:
                try:
                    ActionChains(driver).move_to_element(scroll_target).scroll_by_amount(0, 600).perform()
                    time.sleep(0.4)
                except Exception:
                    pass

        # 6. Keys — для мобильной эмуляции (body, т.к. div может не принимать send_keys)
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)
            body.send_keys(Keys.END)
            time.sleep(0.4)
        except Exception:
            pass

        # Считаем отзывы
        try:
            containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
            if not containers:
                containers = driver.find_elements(By.XPATH, "//div[.//div[contains(@class,'_49x36f')]]")
            count = len(containers)
        except Exception:
            count = 0

        if count == last_count:
            no_new_count += 1
            if no_new_count >= 4:
                thread_print("Прокрутка 2GIS: новых отзывов нет, остановка")
                break
        else:
            no_new_count = 0
            thread_print("Прокрутка 2GIS: отзывов %s" % count)
        last_count = count

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)


def extract_reviews(driver, max_days_back=30, max_reviews_limit=100, scroll_to_load=True):
    thread_print("Извлечение отзывов 2GIS (макс. %s, за %s дней)..." % (max_reviews_limit, max_days_back))

    if scroll_to_load:
        thread_print("Прокрутка для подгрузки отзывов...")
        _scroll_to_load_more(driver)
        time.sleep(1)

    cutoff_date = datetime.now() - timedelta(days=max_days_back)
    reviews_data = []
    seen_texts = set()

    try:
        containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
        if not containers:
            containers = driver.find_elements(By.XPATH, "//div[.//div[contains(@class,'_49x36f')]]")
        thread_print("Найдено контейнеров отзывов: %s" % len(containers))

        for container in containers:
            if len(reviews_data) >= max_reviews_limit:
                break

            # Не пропускать по is_displayed(): после прокрутки вниз большинство контейнеров
            # вне viewport, но текст в DOM есть — иначе 233 контейнера дают только 2 отзыва

            try:
                # Официальный ответ ресторана находится ВНУТРИ контейнера div._1k5soqfl —
                # фильтровать по container.text нельзя, иначе отзывы с ответом пропускаются.
                # Текст извлекается только из div._49x36f a, официальный ответ туда не попадёт.
                review = _extract_single_review(container)
                if not review or not review.get("text"):
                    continue

                text_key = review["text"][:100]
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)

                date_str = review.get("date", "")
                if date_str:
                    parsed = parse_review_date(date_str)
                    if parsed:
                        try:
                            review_date = datetime.strptime(parsed, "%Y-%m-%d")
                            if review_date < cutoff_date:
                                continue
                        except (ValueError, TypeError):
                            pass

                review["date"] = parse_review_date(date_str) or date_str
                reviews_data.append(review)
                thread_print("   #%s: %s - %s..." % (len(reviews_data), review.get("author", "?"), review["text"][:50]))

            except Exception as e:
                thread_print("   Ошибка отзыва: %s" % e)
                continue

        thread_print("Извлечено отзывов: %s" % len(reviews_data))
        return reviews_data

    except Exception as e:
        thread_print("Ошибка извлечения отзывов 2GIS: %s" % e)
        return reviews_data
