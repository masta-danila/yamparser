-- Скрипт создания базы данных reviews и таблицы yandexmaps
-- Автор: Система управления отзывами Yandex Maps
-- Дата создания: 2024

-- Создаем базу данных reviews (если не существует)
-- Примечание: эта команда должна выполняться от пользователя с правами создания БД
-- CREATE DATABASE reviews WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C';

-- Подключаемся к базе данных reviews
-- \c reviews;

-- Создаем таблицу yandexmaps для хранения отзывов
CREATE TABLE IF NOT EXISTS yandexmaps (
    -- Первичный ключ
    id SERIAL PRIMARY KEY,
    
    -- Основные поля отзыва
    card_id VARCHAR(50) NOT NULL,                   -- ID карточки организации
    author_name VARCHAR(255) NOT NULL,              -- Ник автора отзыва
    review_text TEXT NOT NULL,                      -- Полный текст отзыва
    review_date DATE NOT NULL,                      -- Дата написания отзыва
    rating DECIMAL(2,1) CHECK (rating >= 1.0 AND rating <= 5.0), -- Оценка от 1.0 до 5.0
    
    -- Статус обработки
    status VARCHAR(20) DEFAULT 'not_found' CHECK (status IN ('found', 'not_found')),
    
    -- Поля для оптимизации поиска дубликатов
    text_hash VARCHAR(32),                          -- MD5 хеш текста для быстрого сравнения
    text_preview VARCHAR(100),                      -- Первые 100 символов текста
    text_length INTEGER,                            -- Длина полного текста
    
    -- Служебные поля
    created_at TIMESTAMP DEFAULT NOW(),             -- Когда запись добавлена в БД
    updated_at TIMESTAMP DEFAULT NOW()              -- Когда запись последний раз обновлена
);

-- ===============================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ЗАПРОСОВ
-- ===============================

-- 1. Основной индекс по card_id для быстрого поиска отзывов организации
CREATE INDEX IF NOT EXISTS idx_yandexmaps_card_id ON yandexmaps(card_id);

-- 2. Индекс по дате для сортировки (новые сначала)
CREATE INDEX IF NOT EXISTS idx_yandexmaps_date ON yandexmaps(review_date DESC);

-- 3. Составной индекс для checkpoint системы (поиск последнего отзыва)
CREATE INDEX IF NOT EXISTS idx_yandexmaps_checkpoint ON yandexmaps(card_id, review_date DESC, id DESC);

-- 4. ГЛАВНЫЙ ИНДЕКС для алгоритма уникальности (card_id + date + author + rating)
-- Используется для быстрого поиска дубликатов по нашему алгоритму
CREATE INDEX IF NOT EXISTS idx_reviews_uniqueness 
ON yandexmaps(card_id, review_date, author_name, rating);

-- 5. Индекс для быстрой проверки дубликатов по хешу текста
CREATE INDEX IF NOT EXISTS idx_yandexmaps_text_hash ON yandexmaps(text_hash);

-- 6. Индекс по статусу для фильтрации
CREATE INDEX IF NOT EXISTS idx_yandexmaps_status ON yandexmaps(status);

-- 7. Составной индекс для статистики по рейтингам
CREATE INDEX IF NOT EXISTS idx_yandexmaps_card_rating 
ON yandexmaps(card_id, rating) WHERE rating IS NOT NULL;

-- 8. Полнотекстовый индекс для поиска по содержанию отзывов (русский язык)
CREATE INDEX IF NOT EXISTS idx_yandexmaps_fulltext 
ON yandexmaps USING gin(to_tsvector('russian', review_text));

-- 9. Уникальный составной индекс для предотвращения точных дубликатов
-- (один автор не может оставить два одинаковых отзыва в один день на одну карточку)
CREATE UNIQUE INDEX IF NOT EXISTS idx_yandexmaps_unique_review 
ON yandexmaps(card_id, author_name, review_date, text_hash);

-- Создаем функцию для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создаем триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_yandexmaps_updated_at ON yandexmaps;
CREATE TRIGGER update_yandexmaps_updated_at
    BEFORE UPDATE ON yandexmaps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Добавляем комментарии к таблице и полям
COMMENT ON TABLE yandexmaps IS 'Таблица для хранения отзывов с Yandex Maps';
COMMENT ON COLUMN yandexmaps.id IS 'Уникальный идентификатор записи';
COMMENT ON COLUMN yandexmaps.card_id IS 'ID карточки организации на Yandex Maps';
COMMENT ON COLUMN yandexmaps.author_name IS 'Имя автора отзыва';
COMMENT ON COLUMN yandexmaps.review_text IS 'Полный текст отзыва';
COMMENT ON COLUMN yandexmaps.review_date IS 'Дата написания отзыва';
COMMENT ON COLUMN yandexmaps.rating IS 'Оценка от 1.0 до 5.0 (с десятыми)';
COMMENT ON COLUMN yandexmaps.status IS 'Статус обработки: found/not_found';
COMMENT ON COLUMN yandexmaps.text_hash IS 'MD5 хеш текста для быстрого сравнения';
COMMENT ON COLUMN yandexmaps.text_preview IS 'Первые 100 символов текста';
COMMENT ON COLUMN yandexmaps.text_length IS 'Длина полного текста в символах';
COMMENT ON COLUMN yandexmaps.created_at IS 'Время создания записи';
COMMENT ON COLUMN yandexmaps.updated_at IS 'Время последнего обновления записи';

-- ===============================
-- ИНФОРМАЦИЯ О СОЗДАННОЙ СТРУКТУРЕ
-- ===============================

-- Выводим информацию о созданной таблице
SELECT 'База данных и таблица yandexmaps успешно созданы!' as result;

-- Показываем все созданные индексы
SELECT 
    schemaname as "Схема",
    tablename as "Таблица", 
    indexname as "Индекс",
    indexdef as "Определение"
FROM pg_indexes 
WHERE tablename = 'yandexmaps' 
ORDER BY indexname;

-- Показываем статистику таблицы
SELECT 
    'yandexmaps' as "Таблица",
    COUNT(*) as "Количество записей",
    pg_size_pretty(pg_total_relation_size('yandexmaps')) as "Размер таблицы"
FROM yandexmaps; 