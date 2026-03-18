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
TEXT_SELECTOR = "a._1wlx08h"
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


def _scroll_to_load_more(driver, scroll_pauses=3, max_scrolls=15):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_count += 1
            if scroll_count >= scroll_pauses:
                break
        else:
            scroll_count = 0
        last_height = new_height


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
            containers = driver.find_elements(By.XPATH, "//div[.//a[contains(@class, '_1wlx08h')]]")
        thread_print("Найдено контейнеров отзывов: %s" % len(containers))

        for container in containers:
            if len(reviews_data) >= max_reviews_limit:
                break

            if not container.is_displayed():
                continue

            try:
                container_text = (container.text or "").lower()
                if any(
                    phrase in container_text
                    for phrase in [
                        "официальный ответ",
                        "официальный ответ организации",
                        "ответ организации",
                    ]
                ):
                    continue

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
