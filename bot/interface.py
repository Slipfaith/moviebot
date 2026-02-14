from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

QUICK_BUTTON_RECOMMEND = "✨ Рекомендовать"
QUICK_BUTTON_ADD = "➕ Добавить"
QUICK_BUTTON_LAST = "📝 Последние"
QUICK_BUTTON_RANDOM = "🎲 Случайный"
QUICK_BUTTON_STATS = "📊 Статистика"
QUICK_BUTTON_MENU = "📋 Меню"


def get_quick_actions_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(QUICK_BUTTON_RECOMMEND),
            KeyboardButton(QUICK_BUTTON_ADD),
            KeyboardButton(QUICK_BUTTON_LAST),
        ],
        [
            KeyboardButton(QUICK_BUTTON_RANDOM),
            KeyboardButton(QUICK_BUTTON_STATS),
            KeyboardButton(QUICK_BUTTON_MENU),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие",
    )


def _back_button() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("⬅️ Назад", callback_data="menu_main")]


def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Добавить запись", callback_data="add_film")],
        [
            InlineKeyboardButton("✨ Новые рекомендации", callback_data="recommend_me"),
            InlineKeyboardButton("🎲 Случайный", callback_data="random_pick"),
        ],
        [
            InlineKeyboardButton("🎞 Библиотека", callback_data="menu_library"),
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("🧠 AI и подборки", callback_data="menu_recommend"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recommend_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✨ Новые рекомендации", callback_data="recommend_me")],
        [InlineKeyboardButton("🤖 AI-вопрос", callback_data="ai_help")],
        [InlineKeyboardButton("🎲 Случайный фильм", callback_data="random_pick")],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_library_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📝 Последние добавления", callback_data="list_films")],
        [
            InlineKeyboardButton("🗓 За месяц", callback_data="recent_entries"),
            InlineKeyboardButton("🏆 Топ 5", callback_data="top5"),
        ],
        [
            InlineKeyboardButton("🔍 Поиск по названию", callback_data="search_title"),
            InlineKeyboardButton("🎭 По жанру", callback_data="search_genre"),
        ],
        [InlineKeyboardButton("🎲 Случайный", callback_data="random_pick")],
        [InlineKeyboardButton("✨ Раздел рекомендаций", callback_data="menu_recommend")],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_stats_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 Оценки и сводка", callback_data="rating_stats")],
        [InlineKeyboardButton("🏁 Победитель месяца", callback_data="winner_month")],
        [
            InlineKeyboardButton("👨 Подборка: муж", callback_data="owner_husband"),
            InlineKeyboardButton("👩 Подборка: жена", callback_data="owner_wife"),
        ],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_help_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📘 Команды", callback_data="help")],
        [InlineKeyboardButton("ℹ️ Оффлайн-режим", callback_data="offline_help")],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)
