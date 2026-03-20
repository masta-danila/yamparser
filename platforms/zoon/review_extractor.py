"""
Извлечение отзывов со страницы Zoon.ru.

Структура отзыва:
- Контейнер: li.comment-item.js-comment (только верхнеуровневые, не ответы)
- Автор: data-author на li или strong.comment-item__header-name
- Дата: div.z-text--13.z-text--dark-gray в header
- Рейтинг: div[data-uitest="personal-mark"] или meta[itemprop="ratingValue"]
- Текст: span.js-comment-content + span.js-comment-additional-text
  (второй блок с классом hidden — в DOM есть, кликать «показать» не нужно)
"""

from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from thread_logger import thread_print

try:
    from reviews_parser import parse_review_date
except ImportError:
    def parse_review_date(s):
        return s


# Только верхнеуровневые отзывы (не ответы заведения)
REVIEW_CONTAINER = "ul.js-feedbacks-new > li.comment-item.js-comment"
# Fallback: любой li.comment-item, но фильтруем по родителю
REVIEW_ITEM_SELECTOR = "li.comment-item.js-comment"

AUTHOR_ATTR = "data-author"
AUTHOR_SELECTOR = "strong.comment-item__header-name span[itemprop='name']"
DATE_SELECTOR = "div.comment-item__header div.z-text--13.z-text--dark-gray"
RATING_SELECTOR = "div[data-uitest='personal-mark']"
RATING_META = "meta[itemprop='ratingValue']"
# Текст: короткая часть + скрытая часть (оба в DOM)
TEXT_SHORT = "span.js-comment-content"
TEXT_ADDITIONAL = "span.js-comment-additional-text"


def _get_text(container):
    """
    Собирает полный текст: js-comment-content + js-comment-additional-text.
    Скрытый блок (js-comment-additional-text) Selenium .text не возвращает —
    используем textContent через JS.
    """
    parts = []
    try:
        short = container.find_element(By.CSS_SELECTOR, TEXT_SHORT)
        txt_visible = short.text
        txt_content = short.get_attribute("textContent") or ""
        thread_print("DEBUG short .text='%s' textContent='%s'" % (repr(txt_visible[:40]), repr(txt_content[:40])))
        txt = txt_visible or txt_content
        parts.append(txt.strip())
    except Exception as e:
        thread_print("DEBUG short not found: %s" % e)
    try:
        additional = container.find_element(By.CSS_SELECTOR, TEXT_ADDITIONAL)
        # Скрытый элемент: .text пустой, берём textContent
        txt = additional.get_attribute("textContent") or additional.text or ""
        parts.append(txt.strip())
    except Exception:
        pass
    return " ".join(p for p in parts if p)


def _extract_single_review(container):
    """Извлекает данные одного отзыва из li.comment-item."""
    try:
        review_data = {"author": "Аноним", "date": "", "rating": None, "text": ""}

        text = _get_text(container)
        thread_print("DEBUG _get_text: '%s'" % text[:80] if text else "DEBUG _get_text: EMPTY")
        if not text:
            return None

        # Автор: data-author или span[itemprop="name"]
        try:
            author = container.get_attribute(AUTHOR_ATTR)
            if author and author.strip():
                review_data["author"] = author.strip()
        except Exception:
            pass
        if review_data["author"] == "Аноним":
            try:
                author_el = container.find_element(By.CSS_SELECTOR, AUTHOR_SELECTOR)
                author = (author_el.text or "").strip()
                if author:
                    review_data["author"] = author
            except Exception:
                pass

        review_data["text"] = text

        # Дата
        try:
            date_el = container.find_element(By.CSS_SELECTOR, DATE_SELECTOR)
            review_data["date"] = (date_el.text or "").strip()
        except Exception:
            pass

        # Рейтинг: число из div или meta
        try:
            rating_el = container.find_element(By.CSS_SELECTOR, RATING_SELECTOR)
            raw = (rating_el.text or "").strip().replace(",", ".")
            if raw:
                review_data["rating"] = float(raw)
        except Exception:
            try:
                meta = container.find_element(By.CSS_SELECTOR, RATING_META)
                val = meta.get_attribute("content")
                if val:
                    review_data["rating"] = int(val)
            except Exception:
                pass

        return review_data
    except Exception:
        return None


def _is_top_level_review(item):
    """Проверяет, что это верхнеуровневый отзыв, а не вложенный ответ."""
    try:
        parent = item.find_element(By.XPATH, "./..")
        parent_class = parent.get_attribute("class") or ""
        return "comment-item__children" not in parent_class
    except Exception:
        return True


def _get_oldest_visible_date(driver):
    """
    Быстро получает дату последнего (самого старого) видимого отзыва.
    Возвращает datetime или None. Отзывы идут сверху вниз (новые первые).
    """
    try:
        containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
        if not containers:
            return None
        for c in reversed(containers):
            try:
                author = c.get_attribute(AUTHOR_ATTR) or ""
                if "официальн" in author.lower() or "заведени" in author.lower():
                    continue
                date_el = c.find_element(By.CSS_SELECTOR, DATE_SELECTOR)
                raw = (date_el.text or "").strip()
                if not raw:
                    continue
                parsed = parse_review_date(raw)
                if parsed:
                    return datetime.strptime(parsed, "%Y-%m-%d")
            except Exception:
                continue
    except Exception:
        pass
    return None


def _max_scroll_attempts_from_target_date(target_date_str):
    """
    Ограничивает прокрутку по целевой дате искомого отзыва.
    Если ищем отзыв от 05.03.2026 — не крутим все 15 раз, а только сколько нужно.
    """
    if not target_date_str:
        return 15
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d")
        days_ago = (datetime.now() - target).days
        if days_ago <= 7:
            return 3
        if days_ago <= 14:
            return 5
        if days_ago <= 30:
            return 8
        if days_ago <= 90:
            return 12
    except (ValueError, TypeError):
        pass
    return 15


def extract_reviews(driver, max_days_back=30, max_reviews_limit=100, scroll_to_load=True, target_date=None):
    """
    Извлекает отзывы Zoon: парсинг, при необходимости — прокрутка.
    target_date (YYYY-MM-DD) — если искомый отзыв уже на первом экране (05.03.2026),
    прокрутка не выполняется. Скроллим только пока не пройдём целевую дату.
    Возвращает список dict: author, date, rating, text.
    """
    import time

    # Ожидаем появления списка отзывов (контент может подгружаться после клика по вкладке)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.js-feedbacks-new"))
        )
    except Exception:
        pass

    target_dt = None
    if target_date:
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    if scroll_to_load and target_dt:
        from .scroll_reviews import scroll_zoon_one_batch
        max_attempts = _max_scroll_attempts_from_target_date(target_date)
        scroll_count = 0
        while scroll_count < max_attempts:
            oldest = _get_oldest_visible_date(driver)
            if oldest is not None and oldest <= target_dt:
                if scroll_count == 0:
                    thread_print("Прокрутка Zoon: целевой отзыв уже на экране, прокрутка не нужна")
                else:
                    thread_print("Прокрутка Zoon: целевая дата %s достигнута (последний отзыв %s), остановка" % (target_date, oldest.strftime("%Y-%m-%d")))
                break
            clicked = scroll_zoon_one_batch(driver)
            scroll_count += 1
            if clicked:
                thread_print("Прокрутка Zoon: загружена порция (%s)" % scroll_count)
            else:
                thread_print("Прокрутка Zoon: кнопка «Показать еще» не найдена, остановка")
                break
            time.sleep(0.5)
    elif scroll_to_load:
        # Сначала пробуем извлечь без прокрутки — при 1 отзыве прокрутка может мешать
        pre_containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
        if not pre_containers:
            all_pre = driver.find_elements(By.CSS_SELECTOR, REVIEW_ITEM_SELECTOR)
            pre_containers = [c for c in all_pre if _is_top_level_review(c)]
        if not pre_containers:
            from .scroll_reviews import scroll_zoon_reviews
            max_attempts = _max_scroll_attempts_from_target_date(None)
            thread_print("Прокрутка Zoon для подгрузки отзывов (макс. %s кликов)..." % max_attempts)
            scroll_zoon_reviews(driver, max_attempts=max_attempts)
            time.sleep(1)

    cutoff_date = datetime.now() - timedelta(days=max_days_back)
    reviews_data = []
    seen_texts = set()

    try:
        containers = driver.find_elements(By.CSS_SELECTOR, REVIEW_CONTAINER)
        # Fallback: если основной селектор не нашёл — берём все li, исключая вложенные ответы
        if not containers:
            all_items = driver.find_elements(By.CSS_SELECTOR, REVIEW_ITEM_SELECTOR)
            containers = [c for c in all_items if _is_top_level_review(c)]
            if containers:
                thread_print("Zoon: использован fallback-селектор (найдено %s)" % len(containers))
        thread_print("Найдено контейнеров отзывов Zoon: %s" % len(containers))

        for container in containers:
            if len(reviews_data) >= max_reviews_limit:
                break
            try:
                author = container.get_attribute(AUTHOR_ATTR) or ""
                if "официальн" in author.lower() or "заведени" in author.lower():
                    continue
                data = _extract_single_review(container)
                if not data or not data.get("text"):
                    continue
                text_key = data["text"][:100]
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)
                date_str = data.get("date", "")
                if date_str:
                    parsed = parse_review_date(date_str)
                    if parsed:
                        try:
                            review_date = datetime.strptime(parsed, "%Y-%m-%d")
                            if review_date < cutoff_date:
                                continue
                        except (ValueError, TypeError):
                            pass
                data["date"] = parse_review_date(date_str) or date_str
                reviews_data.append(data)
                thread_print("   #%s: %s - %s..." % (len(reviews_data), data.get("author", "?"), data["text"][:50]))
            except Exception as e:
                thread_print("   Ошибка отзыва Zoon: %s" % e)
                continue

    except Exception as e:
        thread_print("Ошибка извлечения отзывов Zoon: %s" % e)

    thread_print("Извлечено отзывов Zoon: %s" % len(reviews_data))
    return reviews_data
