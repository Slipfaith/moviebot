"""Shared user-facing UI texts for Telegram menus and hints."""

from __future__ import annotations

from bot.commands import (
    COMMAND_ADD,
    COMMAND_AI,
    COMMAND_FIND,
    COMMAND_HELP,
    COMMAND_MENU,
    COMMAND_OWNER,
    COMMAND_RANDOM,
    COMMAND_SEARCH,
    slash,
)

QUICK_BUTTON_RECOMMEND = "✨ Рекомендовать"
QUICK_BUTTON_ADD = "➕ Добавить"
QUICK_BUTTON_LAST = "📝 Последние"
QUICK_BUTTON_RANDOM = "🎲 Случайный"
QUICK_BUTTON_STATS = "📊 Статистика"
QUICK_BUTTON_MENU = "📋 Меню"
QUICK_ACTIONS_PLACEHOLDER = "Выберите действие"

PANEL_TITLE_START = "Выберите раздел:"
PANEL_TITLE_MAIN = "Главное меню:"
PANEL_TITLE_RECOMMEND = "Раздел рекомендаций:"
PANEL_TITLE_LIBRARY = "Библиотека:"
PANEL_TITLE_STATS = "Статистика и подборки:"
PANEL_TITLE_HELP = "Помощь:"

QUICK_BUTTONS_HINT_TEXT = "Быстрые кнопки внизу."
RECOMMEND_LOADING_TEXT = "Подбираю рекомендации..."
UNKNOWN_TEXT_GUIDE = f"Используйте {slash(COMMAND_MENU)}, {slash(COMMAND_HELP)} или кнопки снизу."

SEARCH_GENRE_HINT_TEXT = f"Используйте команду: {slash(COMMAND_FIND, ' <жанр>')}"
SEARCH_TITLE_HINT_TEXT = f"Используйте команду: {slash(COMMAND_SEARCH, ' <часть названия>')}"
AI_HELP_HINT_TEXT = f"Спросите AI: {slash(COMMAND_AI, ' <ваш вопрос или запрос по фильмам>')}"

BUTTON_BACK = "⬅️ Назад"
BUTTON_ADD_ENTRY = "➕ Добавить запись"
BUTTON_NEW_RECOMMENDATIONS = "✨ Новые рекомендации"
BUTTON_RANDOM = "🎲 Случайный"
BUTTON_LIBRARY = "🎞 Библиотека"
BUTTON_STATS = "📊 Статистика"
BUTTON_AI_AND_COLLECTIONS = "🧠 AI и подборки"
BUTTON_HELP = "❓ Помощь"

BUTTON_AI_QUESTION = "🤖 AI-вопрос"
BUTTON_RANDOM_FILM = "🎲 Случайный фильм"
BUTTON_LAST_ENTRIES = "📝 Последние добавления"
BUTTON_MONTH = "🗓 За месяц"
BUTTON_TOP5 = "🏆 Топ 5"
BUTTON_SEARCH_TITLE = "🔍 Поиск по названию"
BUTTON_SEARCH_GENRE = "🎭 По жанру"
BUTTON_RECOMMEND_SECTION = "✨ Раздел рекомендаций"
BUTTON_STATS_SUMMARY = "📊 Оценки и сводка"
BUTTON_MONTH_WINNER = "🏁 Победитель месяца"
BUTTON_OWNER_HUSBAND = "👨 Подборка: муж"
BUTTON_OWNER_WIFE = "👩 Подборка: жена"
BUTTON_TOKEN_USAGE = "🧮 AI токены"
BUTTON_TOKEN_USAGE_RESET = "♻️ Обнулить токены"
BUTTON_COMMANDS = "📘 Команды"
BUTTON_OFFLINE_MODE = "ℹ️ Оффлайн-режим"

ADD_FLOW_PROMPT_TITLE = "Введите название фильма или сериала:"
ADD_FLOW_PROMPT_YEAR = "Год выпуска (например, 2014):"
ADD_FLOW_PROMPT_YEAR_INVALID = "Введите год из 4 цифр (например, 2014):"
ADD_FLOW_PROMPT_GENRE = "Жанр (например, фантастика):"
ADD_FLOW_PROMPT_GENRE_INVALID = "Введите жанр (например, фантастика):"
ADD_FLOW_PROMPT_RATING = "Оценка от 1 до 10 (например, 8.5):"
ADD_FLOW_PROMPT_RATING_INVALID = "Введите число от 1 до 10 (например, 8 или 8.5):"
ADD_FLOW_PROMPT_COMMENT = "Комментарий (можно пропустить):"
ADD_FLOW_PROMPT_TYPE = "Тип записи:"
ADD_FLOW_PROMPT_RECOMMENDATION = "Рекомендация:"
ADD_FLOW_PROMPT_OWNER = "Кто добавил?"

ADD_FLOW_ERROR_INVALID_DATA = "Некорректные данные."
ADD_FLOW_ERROR_PARSE_FAILED = "Не удалось разобрать данные для добавления."
ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE = "Данные не найдены. Попробуйте {add_command} заново."
ADD_FLOW_ERROR_BUILD_FAILED_TEMPLATE = "Не удалось собрать данные. Попробуйте {add_command} заново."
ADD_FLOW_MSG_OFFLINE_SAVED = (
    "⚠️ Сейчас нет связи с таблицей. Запись сохранена оффлайн и будет выгружена позже."
)
ADD_FLOW_MSG_SAVED = "✅ Запись добавлена в таблицу."
ADD_FLOW_MSG_SAVED_TEMPLATE = '✅ "{film}" добавлен в таблицу.'
ADD_FLOW_MSG_CANCELLED = "Добавление отменено."
ADD_FLOW_VALUE_DASH = "—"
ADD_FLOW_VALUE_UNSPECIFIED = "не указан"
ADD_FLOW_SKIP_TOKENS = frozenset({"-", "пропустить", "skip", "нет", "без"})
ADD_FLOW_BTN_CONFIRM_SAVE = "✅ Сохранить"
ADD_FLOW_BTN_CONFIRM_CANCEL = "❌ Отмена"
ADD_FLOW_BTN_SKIP_COMMENT = "Пропустить"
ADD_FLOW_BTN_TYPE_FILM = "Фильм"
ADD_FLOW_BTN_TYPE_SERIES = "Сериал"
ADD_FLOW_BTN_REC_RECOMMEND = "рекомендую"
ADD_FLOW_BTN_REC_OK = "можно посмотреть"
ADD_FLOW_BTN_REC_SKIP = "в топку"
ADD_FLOW_BTN_OWNER_HUSBAND = "муж"
ADD_FLOW_BTN_OWNER_WIFE = "жена"
ADD_FLOW_BTN_OWNER_SKIP = "не указывать"
ADD_FLOW_PREVIEW_TEMPLATE = (
    "📋 <b>Проверьте данные перед сохранением:</b>\n\n"
    "🎬 <b>{film}</b> ({year})\n"
    "Жанр: {genre}\n"
    "Оценка: {rating}/10\n"
    "Тип: {entry_type}\n"
    "Рекомендация: {recommendation}\n"
    "Владелец: {owner}\n"
    "Комментарий: {comment}"
)
ADD_FLOW_POSTER_EDITOR_TEMPLATE = (
    "🧩 <b>Карточка из постера</b>\n"
    "Нажмите нужное поле ниже, чтобы исправить его перед сохранением.\n\n"
    "🎬 <b>{film}</b> ({year})\n"
    "Жанр: {genre}\n"
    "Оценка: {rating}/10\n"
    "Тип: {entry_type}\n"
    "Рекомендация: {recommendation}\n"
    "Владелец: {owner}\n"
    "Комментарий: {comment}"
)
ADD_FLOW_POSTER_EDITOR_NOTE_TEMPLATE = "\n\nℹ️ {note}"
ADD_FLOW_EDIT_PROMPT_TITLE = "Введите название фильма:"
ADD_FLOW_EDIT_PROMPT_YEAR = "Введите год (4 цифры, например 2014):"
ADD_FLOW_EDIT_PROMPT_GENRE = "Введите жанр:"
ADD_FLOW_EDIT_PROMPT_RATING = "Введите оценку от 1 до 10:"
ADD_FLOW_EDIT_PROMPT_COMMENT = "Введите комментарий (или '-' чтобы очистить):"
ADD_FLOW_EDIT_PROMPT_TYPE = "Выберите тип:"
ADD_FLOW_EDIT_PROMPT_RECOMMENDATION = "Выберите рекомендацию:"
ADD_FLOW_EDIT_PROMPT_OWNER = "Кто добавил?"
ADD_FLOW_EDIT_MSG_SELECT_FIELD_FIRST = "Сначала выберите поле кнопкой ниже."
ADD_FLOW_EDIT_MSG_INVALID_YEAR = "Год должен быть из 4 цифр (например, 2014)."
ADD_FLOW_EDIT_MSG_INVALID_RATING = "Оценка должна быть числом от 1 до 10."
ADD_FLOW_EDIT_MSG_REQUIRED_TEMPLATE = "Заполните обязательные поля: {missing}."
ADD_FLOW_BTN_EDIT_TITLE = "🎬 Название"
ADD_FLOW_BTN_EDIT_YEAR = "📅 Год"
ADD_FLOW_BTN_EDIT_GENRE = "🎭 Жанр"
ADD_FLOW_BTN_EDIT_RATING = "⭐ Оценка"
ADD_FLOW_BTN_EDIT_COMMENT = "📝 Комментарий"
ADD_FLOW_BTN_EDIT_TYPE = "🎞 Тип"
ADD_FLOW_BTN_EDIT_RECOMMENDATION = "💬 Рекомендация"
ADD_FLOW_BTN_EDIT_OWNER = "👤 Кто добавил"
ADD_FLOW_BTN_EDIT_BACK = "⬅️ Назад"
VOICE_ADD_MSG_NEEDS_MISTRAL_KEY = "Для голосового добавления нужен MISTRALAPI в .env."
VOICE_ADD_MSG_TRANSCRIBE_FAILED = "Не удалось распознать голосовое сообщение. Попробуйте ещё раз."
VOICE_ADD_MSG_PARSE_FAILED = (
    "Не удалось разобрать данные из голосового. "
    "Продиктуйте: название, год, жанр, оценку, тип, рекомендацию и владельца."
)
VOICE_ADD_MSG_INCOMPLETE_TEMPLATE = (
    "Распознал голосовое, но не хватает обязательных полей.\n"
    "Транскрипт: {transcript}\n\n"
    "Нужно минимум: название, год, жанр и оценка."
)
VOICE_ADD_MSG_RECOGNIZED_TEMPLATE = "Распознал: {transcript}"
VOICE_ADD_MSG_CLARIFY_TEMPLATE = (
    "Нужно уточнить данные: {missing}.\n"
    "Отправьте уточнение текстом или новым голосовым."
)
VOICE_ADD_BTN_CLARIFY_TEXT = "⌨️ Уточнить текстом"
VOICE_ADD_BTN_CLARIFY_VOICE = "🎤 Уточнить голосом"
VOICE_ADD_BTN_CLARIFY_CANCEL = "❌ Отмена"

AI_MSG_GEMINI_NOT_CONFIGURED = (
    "AI is not configured. Set GEMINI_API_KEY or MISTRALAPI in .env and restart the bot."
)
AI_MSG_GEMINI_BLOCKED = "Gemini blocked this request. Please rephrase it."
AI_MSG_GEMINI_TEMP_UNAVAILABLE = (
    "Gemini is temporarily unavailable. Please try again in a minute."
)
AI_MSG_GEMINI_NO_RESPONSE = "Could not get a response from Gemini. Please try later."
AI_MSG_USAGE_TEMPLATE = "Usage: {ai_usage}"

RANDOM_VALUE_UNKNOWN = "—"
RANDOM_RATINGS_UNKNOWN = "нет данных"
RANDOM_REASON_DEFAULT = "Похоже по жанру и оценкам на ваши высоко оцененные фильмы."
RANDOM_PICK_TEMPLATE = (
    "🎲 Новый случайный фильм (еще не смотрели):\n"
    "<b>{title} ({year})</b>\n"
    "Жанры: {genres}\n"
    "Рейтинг: {ratings}\n"
    "Почему: {reason}"
)
RANDOM_PLOT_TEMPLATE = "\nСюжет: {plot}"
RANDOM_MSG_NO_RECORDS = "Пока нет записей. Добавьте фильмы, чтобы подбирать новые похожие."
RANDOM_AI_PICK_TEMPLATE = (
    "🎲 Новый случайный фильм (еще не смотрели):\n"
    "<b>{title}</b>\n"
    "Почему: {reason}"
)
RANDOM_MSG_UNAVAILABLE = (
    "Сейчас не получилось подобрать новый фильм вне вашей таблицы.\n"
    "Проверьте доступ к TMDB/AI и попробуйте снова."
)

TOKEN_USAGE_HEADER = "🧮 Расход AI токенов"
TOKEN_USAGE_RESET_NOTE = "Счётчик токенов обнулён пользователем."
TOKEN_USAGE_PERSISTENCE_NOTE = "Счётчик накапливается постоянно и не сбрасывается автоматически."
TOKEN_USAGE_FILE_LABEL = "Файл счётчика"
TOKEN_USAGE_BACKUP_LABEL = "Папка бэкапов"

LIB_FIND_USAGE_TEXT = f"Использование: {slash(COMMAND_FIND, ' <жанр>')}"
LIB_OWNER_USAGE_TEXT = f"Использование: {slash(COMMAND_OWNER, ' <муж|жена>')}"
LIB_SEARCH_USAGE_TEXT = f"Использование: {slash(COMMAND_SEARCH, ' <часть названия>')}"
LIB_FIND_NOT_FOUND_TEXT = (
    "Ничего не найдено. "
    f"Попробуйте {slash(COMMAND_FIND, ' триллер')}, "
    f"{slash(COMMAND_SEARCH, ' матрица')} или {slash(COMMAND_RANDOM)}."
)
LIB_FIND_FOUND_HEADER = "🔎 Найдено:"
LIB_OWNER_HEADER_TEMPLATE = "👤 Подборка ({owner}):"
LIB_OWNER_NOT_FOUND_TEMPLATE = "Для владельца «{owner}» ничего не найдено."
LIB_SEARCH_NOT_FOUND_TEMPLATE = (
    "По запросу «{query}» ничего не найдено.\n"
    f"Попробуйте {slash(COMMAND_FIND, ' <жанр>')} или {slash(COMMAND_RANDOM)} для нового варианта."
)
LIB_SEARCH_RESULTS_HEADER_TEMPLATE = "🔍 Результаты поиска «{query}»:"
LIB_SEARCH_MORE_TEMPLATE = "\n\n...и ещё {count} совпадений. Уточните запрос."

PHOTO_MSG_NOT_FOUND = "Фото не найдено. Отправьте постер фильма."
PHOTO_MSG_NEEDS_GEMINI_KEY = "Для распознавания постера нужен GEMINI_API_KEY."
PHOTO_MSG_DOWNLOAD_FAILED = "Не удалось загрузить фото. Попробуйте ещё раз."
PHOTO_MSG_GEMINI_UNAVAILABLE = "Gemini сейчас недоступен для распознавания фото."
PHOTO_MSG_RECOGNIZE_FAILED = "Не удалось распознать постер. Попробуйте позже."
PHOTO_MSG_PARSE_FAILED = (
    "Не удалось разобрать ответ Gemini по фото. Отправьте более чёткий постер."
)
PHOTO_MSG_TITLE_UNSURE = (
    "Не смог уверенно определить фильм по этому постеру. Попробуйте другое фото."
)
PHOTO_MSG_PREFILL_EXPIRED = "Данные для быстрого добавления устарели. Отправьте постер заново."
PHOTO_BUTTON_ADD_WATCHED = "➕ Добавить в просмотренное"
PHOTO_FOUND_HEADER_TEMPLATE = "🖼 Нашёл по постеру: <b>{title}{year_label}</b>"
PHOTO_TYPE_MOVIE = "фильм"
PHOTO_TYPE_SERIES = "сериал"
PHOTO_TYPE_UNKNOWN = "медиа"
PHOTO_TYPE_TEMPLATE = "Тип: {type_label}"
PHOTO_CONFIDENCE_TEMPLATE = "Уверенность Gemini: {confidence:.0f}%"
PHOTO_REASON_TEMPLATE = "Почему: {reason}"
PHOTO_GENRES_TEMPLATE = "Жанры: {genre}"
PHOTO_IMDB_TEMPLATE = "IMDb: {imdb_rating:.1f}/10"
PHOTO_PLOT_TEMPLATE = "Сюжет: {plot}"
PHOTO_QUICK_ADD_TEMPLATE = (
    f"Быстро добавить: {slash(COMMAND_ADD)} {{title}};{{year}};{{genre}};{{rating}}"
)

__all__ = [
    "QUICK_BUTTON_RECOMMEND",
    "QUICK_BUTTON_ADD",
    "QUICK_BUTTON_LAST",
    "QUICK_BUTTON_RANDOM",
    "QUICK_BUTTON_STATS",
    "QUICK_BUTTON_MENU",
    "QUICK_ACTIONS_PLACEHOLDER",
    "PANEL_TITLE_START",
    "PANEL_TITLE_MAIN",
    "PANEL_TITLE_RECOMMEND",
    "PANEL_TITLE_LIBRARY",
    "PANEL_TITLE_STATS",
    "PANEL_TITLE_HELP",
    "QUICK_BUTTONS_HINT_TEXT",
    "RECOMMEND_LOADING_TEXT",
    "UNKNOWN_TEXT_GUIDE",
    "SEARCH_GENRE_HINT_TEXT",
    "SEARCH_TITLE_HINT_TEXT",
    "AI_HELP_HINT_TEXT",
    "BUTTON_BACK",
    "BUTTON_ADD_ENTRY",
    "BUTTON_NEW_RECOMMENDATIONS",
    "BUTTON_RANDOM",
    "BUTTON_LIBRARY",
    "BUTTON_STATS",
    "BUTTON_AI_AND_COLLECTIONS",
    "BUTTON_HELP",
    "BUTTON_AI_QUESTION",
    "BUTTON_RANDOM_FILM",
    "BUTTON_LAST_ENTRIES",
    "BUTTON_MONTH",
    "BUTTON_TOP5",
    "BUTTON_SEARCH_TITLE",
    "BUTTON_SEARCH_GENRE",
    "BUTTON_RECOMMEND_SECTION",
    "BUTTON_STATS_SUMMARY",
    "BUTTON_MONTH_WINNER",
    "BUTTON_OWNER_HUSBAND",
    "BUTTON_OWNER_WIFE",
    "BUTTON_TOKEN_USAGE",
    "BUTTON_TOKEN_USAGE_RESET",
    "BUTTON_COMMANDS",
    "BUTTON_OFFLINE_MODE",
    "ADD_FLOW_PROMPT_TITLE",
    "ADD_FLOW_PROMPT_YEAR",
    "ADD_FLOW_PROMPT_YEAR_INVALID",
    "ADD_FLOW_PROMPT_GENRE",
    "ADD_FLOW_PROMPT_GENRE_INVALID",
    "ADD_FLOW_PROMPT_RATING",
    "ADD_FLOW_PROMPT_RATING_INVALID",
    "ADD_FLOW_PROMPT_COMMENT",
    "ADD_FLOW_PROMPT_TYPE",
    "ADD_FLOW_PROMPT_RECOMMENDATION",
    "ADD_FLOW_PROMPT_OWNER",
    "ADD_FLOW_ERROR_INVALID_DATA",
    "ADD_FLOW_ERROR_PARSE_FAILED",
    "ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE",
    "ADD_FLOW_ERROR_BUILD_FAILED_TEMPLATE",
    "ADD_FLOW_MSG_OFFLINE_SAVED",
    "ADD_FLOW_MSG_SAVED",
    "ADD_FLOW_MSG_SAVED_TEMPLATE",
    "ADD_FLOW_MSG_CANCELLED",
    "ADD_FLOW_VALUE_DASH",
    "ADD_FLOW_VALUE_UNSPECIFIED",
    "ADD_FLOW_SKIP_TOKENS",
    "ADD_FLOW_BTN_CONFIRM_SAVE",
    "ADD_FLOW_BTN_CONFIRM_CANCEL",
    "ADD_FLOW_BTN_SKIP_COMMENT",
    "ADD_FLOW_BTN_TYPE_FILM",
    "ADD_FLOW_BTN_TYPE_SERIES",
    "ADD_FLOW_BTN_REC_RECOMMEND",
    "ADD_FLOW_BTN_REC_OK",
    "ADD_FLOW_BTN_REC_SKIP",
    "ADD_FLOW_BTN_OWNER_HUSBAND",
    "ADD_FLOW_BTN_OWNER_WIFE",
    "ADD_FLOW_BTN_OWNER_SKIP",
    "ADD_FLOW_PREVIEW_TEMPLATE",
    "ADD_FLOW_POSTER_EDITOR_TEMPLATE",
    "ADD_FLOW_POSTER_EDITOR_NOTE_TEMPLATE",
    "ADD_FLOW_EDIT_PROMPT_TITLE",
    "ADD_FLOW_EDIT_PROMPT_YEAR",
    "ADD_FLOW_EDIT_PROMPT_GENRE",
    "ADD_FLOW_EDIT_PROMPT_RATING",
    "ADD_FLOW_EDIT_PROMPT_COMMENT",
    "ADD_FLOW_EDIT_PROMPT_TYPE",
    "ADD_FLOW_EDIT_PROMPT_RECOMMENDATION",
    "ADD_FLOW_EDIT_PROMPT_OWNER",
    "ADD_FLOW_EDIT_MSG_SELECT_FIELD_FIRST",
    "ADD_FLOW_EDIT_MSG_INVALID_YEAR",
    "ADD_FLOW_EDIT_MSG_INVALID_RATING",
    "ADD_FLOW_EDIT_MSG_REQUIRED_TEMPLATE",
    "ADD_FLOW_BTN_EDIT_TITLE",
    "ADD_FLOW_BTN_EDIT_YEAR",
    "ADD_FLOW_BTN_EDIT_GENRE",
    "ADD_FLOW_BTN_EDIT_RATING",
    "ADD_FLOW_BTN_EDIT_COMMENT",
    "ADD_FLOW_BTN_EDIT_TYPE",
    "ADD_FLOW_BTN_EDIT_RECOMMENDATION",
    "ADD_FLOW_BTN_EDIT_OWNER",
    "ADD_FLOW_BTN_EDIT_BACK",
    "VOICE_ADD_MSG_NEEDS_MISTRAL_KEY",
    "VOICE_ADD_MSG_TRANSCRIBE_FAILED",
    "VOICE_ADD_MSG_PARSE_FAILED",
    "VOICE_ADD_MSG_INCOMPLETE_TEMPLATE",
    "VOICE_ADD_MSG_RECOGNIZED_TEMPLATE",
    "VOICE_ADD_MSG_CLARIFY_TEMPLATE",
    "VOICE_ADD_BTN_CLARIFY_TEXT",
    "VOICE_ADD_BTN_CLARIFY_VOICE",
    "VOICE_ADD_BTN_CLARIFY_CANCEL",
    "AI_MSG_GEMINI_NOT_CONFIGURED",
    "AI_MSG_GEMINI_BLOCKED",
    "AI_MSG_GEMINI_TEMP_UNAVAILABLE",
    "AI_MSG_GEMINI_NO_RESPONSE",
    "AI_MSG_USAGE_TEMPLATE",
    "RANDOM_VALUE_UNKNOWN",
    "RANDOM_RATINGS_UNKNOWN",
    "RANDOM_REASON_DEFAULT",
    "RANDOM_PICK_TEMPLATE",
    "RANDOM_PLOT_TEMPLATE",
    "RANDOM_MSG_NO_RECORDS",
    "RANDOM_AI_PICK_TEMPLATE",
    "RANDOM_MSG_UNAVAILABLE",
    "TOKEN_USAGE_HEADER",
    "TOKEN_USAGE_RESET_NOTE",
    "TOKEN_USAGE_PERSISTENCE_NOTE",
    "TOKEN_USAGE_FILE_LABEL",
    "TOKEN_USAGE_BACKUP_LABEL",
    "LIB_FIND_USAGE_TEXT",
    "LIB_OWNER_USAGE_TEXT",
    "LIB_SEARCH_USAGE_TEXT",
    "LIB_FIND_NOT_FOUND_TEXT",
    "LIB_FIND_FOUND_HEADER",
    "LIB_OWNER_HEADER_TEMPLATE",
    "LIB_OWNER_NOT_FOUND_TEMPLATE",
    "LIB_SEARCH_NOT_FOUND_TEMPLATE",
    "LIB_SEARCH_RESULTS_HEADER_TEMPLATE",
    "LIB_SEARCH_MORE_TEMPLATE",
    "PHOTO_MSG_NOT_FOUND",
    "PHOTO_MSG_NEEDS_GEMINI_KEY",
    "PHOTO_MSG_DOWNLOAD_FAILED",
    "PHOTO_MSG_GEMINI_UNAVAILABLE",
    "PHOTO_MSG_RECOGNIZE_FAILED",
    "PHOTO_MSG_PARSE_FAILED",
    "PHOTO_MSG_TITLE_UNSURE",
    "PHOTO_MSG_PREFILL_EXPIRED",
    "PHOTO_BUTTON_ADD_WATCHED",
    "PHOTO_FOUND_HEADER_TEMPLATE",
    "PHOTO_TYPE_MOVIE",
    "PHOTO_TYPE_SERIES",
    "PHOTO_TYPE_UNKNOWN",
    "PHOTO_TYPE_TEMPLATE",
    "PHOTO_CONFIDENCE_TEMPLATE",
    "PHOTO_REASON_TEMPLATE",
    "PHOTO_GENRES_TEMPLATE",
    "PHOTO_IMDB_TEMPLATE",
    "PHOTO_PLOT_TEMPLATE",
    "PHOTO_QUICK_ADD_TEMPLATE",
]
