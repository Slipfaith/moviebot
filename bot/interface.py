from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎬 Добавить фильм", callback_data="add_film")],
        [InlineKeyboardButton("📜 Список фильмов", callback_data="list_films")]
    ]
    return InlineKeyboardMarkup(keyboard)
