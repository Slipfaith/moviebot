from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎬 Добавить запись", callback_data="add_film")],
        [InlineKeyboardButton("📜 Последние добавления", callback_data="list_films")],
        [
            InlineKeyboardButton("🗓 За месяц", callback_data="recent_entries"),
            InlineKeyboardButton("🏆 Топ 5", callback_data="top5"),
        ],
        [InlineKeyboardButton("🎭 Поиск по жанру", callback_data="search_genre")],
        [InlineKeyboardButton("📊 Статистика по оценкам", callback_data="rating_stats")],
        [InlineKeyboardButton("ℹ️ Как добавить оффлайн", callback_data="offline_help")],
    ]
    return InlineKeyboardMarkup(keyboard)
