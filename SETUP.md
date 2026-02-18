# Как поставить MovieBot себе

## Что нужно заранее

- Компьютер с **Python 3.10+** (скачать: https://python.org)
- Аккаунт в **Telegram**
- Аккаунт **Google** (для хранения данных в Google Sheets)

---

## Шаг 1 — Скачать код

```bash
git clone <ссылка на репозиторий>
cd moviebot
```

---

## Шаг 2 — Получить API ключи

Тебе нужно 5 ключей. Вот где их взять:

### Telegram Token (обязательно)
1. Открой Telegram, найди бота `@BotFather`
2. Напиши `/newbot`, придумай имя боту
3. BotFather пришлёт токен — это длинная строка вида `7755461069:AAG...`

### Google Sheets (обязательно)
Бот хранит все фильмы в таблице Google.

**Создать таблицу:**
1. Открой Google Sheets, создай новую таблицу
2. Скопируй ссылку из адресной строки браузера

**Создать сервисный аккаунт (чтобы бот мог писать в таблицу):**
1. Зайди на https://console.cloud.google.com
2. Создай новый проект (любое название)
3. Включи **Google Sheets API**: меню → "APIs & Services" → "Enable APIs" → найди "Google Sheets API" → включи
4. Создай сервисный аккаунт: "APIs & Services" → "Credentials" → "Create Credentials" → "Service Account"
5. В настройках аккаунта перейди во вкладку "Keys" → "Add Key" → "JSON" — скачается файл
6. Переименуй этот файл в `google_credentials.json` и положи в папку с ботом
7. Открой скачанный JSON, найди строку `"client_email"` — это email вида `xxx@xxx.iam.gserviceaccount.com`
8. Открой свою Google таблицу → кнопка "Поделиться" → добавь этот email с правами **редактора**

### Gemini API (для AI-функций — обязательно)
1. Зайди на https://aistudio.google.com/apikey
2. Нажми "Create API key"
3. Скопируй ключ

### Mistral API (для голосовых сообщений — обязательно)
1. Зайди на https://console.mistral.ai
2. Зарегистрируйся → "API Keys" → "Create new key"
3. Скопируй ключ

### TMDB API (для постеров и метаданных — обязательно)
1. Зайди на https://www.themoviedb.org/settings/api
2. Зарегистрируйся → "Create" → выбери "Developer"
3. Скопируй **API Key (v3 auth)**

### OMDB API (дополнительный источник данных — опционально)
1. Зайди на https://www.omdbapi.com/apikey.aspx
2. Зарегистрируйся бесплатно
3. На почту придёт ключ

### Kinopoisk API (опционально, только для РФ)
1. Зайди на https://kinopoisk.dev
2. Зарегистрируйся и получи API ключ

---

## Шаг 3 — Создать файл `.env`

Создай в папке с ботом файл `.env` и заполни своими ключами:

```env
TELEGRAM_TOKEN=сюда_вставь_токен_от_BotFather

GOOGLE_CREDENTIALS=google_credentials.json
GOOGLE_SHEET_NAME=https://docs.google.com/spreadsheets/d/ТВОЯ_ССЫЛКА/edit

GEMINI_API_KEY=сюда_вставь_ключ_Gemini

MISTRALAPI=сюда_вставь_ключ_Mistral

TMDB_API_KEY=сюда_вставь_ключ_TMDB

# Опционально:
OMDB_API_KEY=сюда_вставь_ключ_OMDB
KINOPOISK_API_KEY=сюда_вставь_ключ_Kinopoisk
```

---

## Шаг 4 — Установить зависимости и запустить

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить бота
python main.py
```

Если в консоли нет ошибок — бот работает. Открой Telegram и напиши своему боту `/start`.

---

## Частые проблемы

| Проблема | Решение |
|---|---|
| `TELEGRAM_TOKEN не найден` | Проверь, что файл `.env` находится в папке с ботом |
| `Spreadsheet not found` | Убедись, что поделился таблицей с email сервисного аккаунта |
| `403 от Google Sheets` | Включи Google Sheets API в Google Cloud Console |
| Бот не отвечает на голос | Проверь ключ `MISTRALAPI` |
