from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎬 Добавить запись", callback_data="add_film")],
        [InlineKeyboardButton("📜 Последние добавления", callback_data="list_films")],
        [InlineKeyboardButton("🎭 Поиск по жанру", callback_data="search_genre")],
        [InlineKeyboardButton("📊 Статистика по оценкам", callback_data="rating_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)
