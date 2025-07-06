"""
Модуль для сравнения текстов отзывов с настраиваемым процентом совпадения
"""

import re
from difflib import SequenceMatcher
from typing import List, Tuple, Optional
from thread_logger import thread_print

class TextMatcher:
    """Класс для сравнения текстов отзывов"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Инициализация матчера
        
        Args:
            similarity_threshold: Порог совпадения (0.0 - 1.0, где 1.0 - полное совпадение)
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize_text(self, text: str) -> str:
        """Нормализация текста для сравнения"""
        if not text:
            return ""
        
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Убираем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        
        # Убираем знаки препинания (кроме важных)
        text = re.sub(r'[^\w\s\-\!\?\.]', '', text)
        
        # Убираем лишние пробелы в начале и конце
        text = text.strip()
        
        return text
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет процент совпадения между двумя текстами
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            Процент совпадения (0.0 - 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Нормализуем тексты
        normalized_text1 = self.normalize_text(text1)
        normalized_text2 = self.normalize_text(text2)
        
        if not normalized_text1 or not normalized_text2:
            return 0.0
        
        # Используем SequenceMatcher для определения схожести
        matcher = SequenceMatcher(None, normalized_text1, normalized_text2)
        similarity = matcher.ratio()
        
        return similarity
    
    def is_match(self, text1: str, text2: str) -> bool:
        """
        Проверяет, совпадают ли тексты согласно установленному порогу
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            True если тексты совпадают, False иначе
        """
        similarity = self.calculate_similarity(text1, text2)
        return similarity >= self.similarity_threshold
    
    def find_best_match(self, target_text: str, candidate_texts: List[str]) -> Optional[Tuple[str, float, int]]:
        """
        Находит лучшее совпадение среди списка текстов
        
        Args:
            target_text: Целевой текст для поиска
            candidate_texts: Список текстов-кандидатов
            
        Returns:
            Кортеж (лучший_текст, процент_совпадения, индекс) или None если совпадений нет
        """
        if not target_text or not candidate_texts:
            return None
        
        best_match = None
        best_similarity = 0.0
        best_index = -1
        
        for i, candidate_text in enumerate(candidate_texts):
            similarity = self.calculate_similarity(target_text, candidate_text)
            
            if similarity >= self.similarity_threshold and similarity > best_similarity:
                best_match = candidate_text
                best_similarity = similarity
                best_index = i
        
        return (best_match, best_similarity, best_index) if best_match else None
    
    def find_matches_in_reviews(self, sheet_reviews: List[dict], parsed_reviews: List[dict]) -> List[dict]:
        """
        Находит совпадения между отзывами из таблицы и спаршенными отзывами
        
        Args:
            sheet_reviews: Отзывы из Google Sheets [{'text': '...', 'row': N, 'url': '...'}]
            parsed_reviews: Спаршенные отзывы [{'text': '...', 'date': '...', 'author': '...'}]
            
        Returns:
            Список совпадений [{'sheet_review': {...}, 'parsed_review': {...}, 'similarity': 0.95}]
        """
        matches = []
        
        if not sheet_reviews or not parsed_reviews:
            return matches
        
        # Извлекаем тексты из спаршенных отзывов
        parsed_texts = [review.get('text', '') for review in parsed_reviews]
        
        for sheet_review in sheet_reviews:
            sheet_text = sheet_review.get('text', '')
            
            if not sheet_text.strip():
                continue
            
            # Ищем лучшее совпадение
            match_result = self.find_best_match(sheet_text, parsed_texts)
            
            if match_result:
                best_text, similarity, index = match_result
                parsed_review = parsed_reviews[index]
                
                match_info = {
                    'sheet_review': sheet_review,
                    'parsed_review': parsed_review,
                    'similarity': similarity,
                    'similarity_percent': round(similarity * 100, 1)
                }
                
                matches.append(match_info)
                
                thread_print(f"✅ Найдено совпадение {match_info['similarity_percent']}%:")
                thread_print(f"   📄 Лист: строка {sheet_review.get('row', '?')}")
                thread_print(f"   📝 Текст из таблицы: {sheet_text[:100]}...")
                thread_print(f"   🌐 Текст с карточки: {best_text[:100]}...")
        
        return matches
    
    def set_threshold(self, threshold: float):
        """
        Устанавливает новый порог совпадения
        
        Args:
            threshold: Новый порог (0.0 - 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
            thread_print(f"🎯 Порог совпадения установлен: {threshold * 100}%")
        else:
            thread_print(f"❌ Неверный порог: {threshold}. Должен быть от 0.0 до 1.0")


def test_text_matcher():
    """Тестирование модуля сравнения текстов"""
    print("🧪 Тестирование TextMatcher...")
    
    matcher = TextMatcher(similarity_threshold=0.8)
    
    # Тестовые тексты
    text1 = "Отличное место! Очень вкусная еда и приятная атмосфера."
    text2 = "Отличное место! Очень вкусная еда и приятная атмосфера."  # Точное совпадение
    text3 = "Отличное место! Вкусная еда и хорошая атмосфера."  # Похожий текст
    text4 = "Ужасное место, не рекомендую."  # Совсем другой текст
    
    print(f"Текст 1: {text1}")
    print(f"Текст 2: {text2}")
    print(f"Текст 3: {text3}")
    print(f"Текст 4: {text4}")
    print()
    
    # Тестируем совпадения
    similarity_1_2 = matcher.calculate_similarity(text1, text2)
    similarity_1_3 = matcher.calculate_similarity(text1, text3)
    similarity_1_4 = matcher.calculate_similarity(text1, text4)
    
    print(f"Совпадение 1-2: {similarity_1_2:.2%}")
    print(f"Совпадение 1-3: {similarity_1_3:.2%}")
    print(f"Совпадение 1-4: {similarity_1_4:.2%}")
    print()
    
    # Тестируем is_match
    print(f"Совпадают ли 1-2? {matcher.is_match(text1, text2)}")
    print(f"Совпадают ли 1-3? {matcher.is_match(text1, text3)}")
    print(f"Совпадают ли 1-4? {matcher.is_match(text1, text4)}")
    print()
    
    # Тестируем find_best_match
    candidates = [text2, text3, text4]
    best_match = matcher.find_best_match(text1, candidates)
    
    if best_match:
        best_text, similarity, index = best_match
        print(f"Лучшее совпадение: индекс {index}, совпадение {similarity:.2%}")
        print(f"Текст: {best_text}")
    else:
        print("Совпадений не найдено")


if __name__ == "__main__":
    test_text_matcher() 