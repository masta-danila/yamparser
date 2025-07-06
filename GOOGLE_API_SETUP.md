# 🔐 Настройка Google Sheets API - Пошаговая инструкция

## 📋 Что нужно для доступа к приватным Google Sheets

Ваша таблица приватная, поэтому нужны **API ключи**. Вот полная инструкция:

## 🚀 ШАГ 1: Создание Google Cloud проекта

1. **Перейдите в Google Cloud Console:**
   - Откройте: https://console.cloud.google.com/
   - Войдите в ваш Google аккаунт

2. **Создайте новый проект:**
   - Нажмите на выпадающий список проектов (сверху)
   - Выберите "New Project" / "Создать проект"
   - Название: `Google Sheets Reader`
   - Нажмите "Create" / "Создать"

## 🔌 ШАГ 2: Включение Google Sheets API

1. **В Google Cloud Console:**
   - Перейдите в **APIs & Services** → **Library**
   - Или ссылка: https://console.cloud.google.com/apis/library

2. **Найдите и включите API:**
   - В поиске введите: `Google Sheets API`
   - Нажмите на результат
   - Нажмите **"Enable"** / **"Включить"**

## 🔑 ШАГ 3: Создание учетных данных

### Вариант A: Сервисный аккаунт (рекомендуется)

1. **Создание сервисного аккаунта:**
   - Перейдите в **APIs & Services** → **Credentials**
   - Нажмите **"Create Credentials"** → **"Service account"**

2. **Заполните данные:**
   - **Service account name:** `sheets-reader`
   - **Service account ID:** (автоматически)
   - **Description:** `Для чтения Google Sheets`
   - Нажмите **"Create and Continue"**

3. **Роли (опционально):**
   - Можете пропустить или выбрать **Project** → **Editor**
   - Нажмите **"Continue"** → **"Done"**

4. **Создание ключа:**
   - Найдите созданный сервисный аккаунт в списке
   - Нажмите на email аккаунта
   - Перейдите в раздел **"Keys"**
   - Нажмите **"Add Key"** → **"Create new key"**
   - Выберите формат **JSON**
   - Нажмите **"Create"**

5. **Сохранение файла:**
   - Файл `credentials.json` автоматически скачается
   - **Сохраните его в папку с проектом!**
   - **НЕ ДЕЛИТЕСЬ этим файлом - это секретные ключи!**

## 📤 ШАГ 4: Предоставление доступа к таблице

1. **Откройте ваш Google Sheets:**
   - Ваша таблица: https://docs.google.com/spreadsheets/d/1prLF8cF6wpdGkOdgDyZLZ8MHbG0NbdfN_rVQ-ilYX3Y/edit

2. **Поделитесь с сервисным аккаунтом:**
   - Нажмите **"Share"** / **"Поделиться"** (правый верхний угол)
   - В поле email введите **email из файла credentials.json**
     - Откройте `credentials.json`
     - Найдите поле `"client_email"`
     - Скопируйте значение (например: `sheets-reader@project-123.iam.gserviceaccount.com`)
   - Установите права: **"Editor"** или **"Viewer"** (достаточно Viewer для чтения)
   - Нажмите **"Send"** / **"Отправить"**

## 📦 ШАГ 5: Установка зависимостей

```bash
pip install -r requirements.txt
pip install -r requirements_sheets.txt
```

Или отдельно только для Google Sheets:
```bash
pip install gspread google-auth google-api-python-client openpyxl pandas
```

## 🚀 ШАГ 6: Тестирование

1. **Убедитесь что файл credentials.json в папке проекта**

2. **Запустите:**
```bash
python test_google_sheets_api.py
```

## 🔍 Альтернативный способ: OAuth 2.0 (для личного использования)

Если хотите работать от своего имени (не через сервисный аккаунт):

1. **Создайте OAuth 2.0 credentials:**
   - **APIs & Services** → **Credentials**
   - **"Create Credentials"** → **"OAuth client ID"**
   - Application type: **"Desktop application"**
   - Name: `Google Sheets Reader`

2. **Скачайте JSON файл**
   - Сохраните как `oauth_credentials.json`

3. **При первом запуске:**
   - Откроется браузер для авторизации
   - Разрешите доступ к Google Sheets
   - Токен сохранится автоматически

## 🛡️ Безопасность

- ✅ **НЕ добавляйте credentials.json в Git**
- ✅ **Храните файл в надежном месте**  
- ✅ **Не делитесь ключами**
- ✅ **Используйте минимальные права доступа**

## 🆘 Частые проблемы

### Ошибка 403 Forbidden
- API не включен → вернитесь к шагу 2
- Неправильные права → проверьте доступ к таблице

### Ошибка 404 Not Found  
- Неправильный ID таблицы → проверьте URL
- Нет доступа к таблице → проверьте шаг 4

### FileNotFoundError credentials.json
- Файл не в той папке → переместите в папку проекта
- Неправильное имя файла → переименуйте в `credentials.json`

## 🎯 Что дальше?

После настройки API вы сможете:

✅ **Читать все листы** из любых ваших Google Sheets  
✅ **Автоматически получать данные** без ручного экспорта  
✅ **Интегрировать с другими системами**  
✅ **Создавать автоматические отчеты**

Готовы настроить API? Следуйте инструкции выше! 🚀 