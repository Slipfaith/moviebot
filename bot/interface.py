from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.callback_ids import (
    ADD_FILM,
    AI_HELP,
    HELP,
    LIST_FILMS,
    MENU_HELP,
    MENU_LIBRARY,
    MENU_MAIN,
    MENU_RECOMMEND,
    MENU_STATS,
    OFFLINE_HELP,
    OWNER_HUSBAND,
    OWNER_WIFE,
    RANDOM_PICK,
    RATING_STATS,
    RECENT_ENTRIES,
    RECOMMEND_ME,
    SEARCH_GENRE,
    SEARCH_TITLE,
    TOKEN_USAGE,
    TOP5,
    WINNER_MONTH,
)
from bot.ui_texts import (
    BUTTON_ADD_ENTRY,
    BUTTON_AI_AND_COLLECTIONS,
    BUTTON_AI_QUESTION,
    BUTTON_BACK,
    BUTTON_COMMANDS,
    BUTTON_HELP,
    BUTTON_LAST_ENTRIES,
    BUTTON_LIBRARY,
    BUTTON_MONTH,
    BUTTON_MONTH_WINNER,
    BUTTON_NEW_RECOMMENDATIONS,
    BUTTON_OFFLINE_MODE,
    BUTTON_OWNER_HUSBAND,
    BUTTON_OWNER_WIFE,
    BUTTON_RANDOM,
    BUTTON_RANDOM_FILM,
    BUTTON_RECOMMEND_SECTION,
    BUTTON_SEARCH_GENRE,
    BUTTON_SEARCH_TITLE,
    BUTTON_STATS,
    BUTTON_STATS_SUMMARY,
    BUTTON_TOKEN_USAGE,
    BUTTON_TOP5,
    QUICK_ACTIONS_PLACEHOLDER,
    QUICK_BUTTON_ADD,
    QUICK_BUTTON_LAST,
    QUICK_BUTTON_MENU,
    QUICK_BUTTON_RANDOM,
    QUICK_BUTTON_RECOMMEND,
    QUICK_BUTTON_STATS,
)


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
        input_field_placeholder=QUICK_ACTIONS_PLACEHOLDER,
    )


def _back_button() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(BUTTON_BACK, callback_data=MENU_MAIN)]


def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(BUTTON_ADD_ENTRY, callback_data=ADD_FILM)],
        [
            InlineKeyboardButton(BUTTON_NEW_RECOMMENDATIONS, callback_data=RECOMMEND_ME),
            InlineKeyboardButton(BUTTON_RANDOM, callback_data=RANDOM_PICK),
        ],
        [
            InlineKeyboardButton(BUTTON_LIBRARY, callback_data=MENU_LIBRARY),
            InlineKeyboardButton(BUTTON_STATS, callback_data=MENU_STATS),
        ],
        [
            InlineKeyboardButton(BUTTON_AI_AND_COLLECTIONS, callback_data=MENU_RECOMMEND),
            InlineKeyboardButton(BUTTON_HELP, callback_data=MENU_HELP),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recommend_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(BUTTON_NEW_RECOMMENDATIONS, callback_data=RECOMMEND_ME)],
        [InlineKeyboardButton(BUTTON_AI_QUESTION, callback_data=AI_HELP)],
        [InlineKeyboardButton(BUTTON_RANDOM_FILM, callback_data=RANDOM_PICK)],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_library_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(BUTTON_LAST_ENTRIES, callback_data=LIST_FILMS)],
        [
            InlineKeyboardButton(BUTTON_MONTH, callback_data=RECENT_ENTRIES),
            InlineKeyboardButton(BUTTON_TOP5, callback_data=TOP5),
        ],
        [
            InlineKeyboardButton(BUTTON_SEARCH_TITLE, callback_data=SEARCH_TITLE),
            InlineKeyboardButton(BUTTON_SEARCH_GENRE, callback_data=SEARCH_GENRE),
        ],
        [InlineKeyboardButton(BUTTON_RANDOM, callback_data=RANDOM_PICK)],
        [InlineKeyboardButton(BUTTON_RECOMMEND_SECTION, callback_data=MENU_RECOMMEND)],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_stats_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(BUTTON_STATS_SUMMARY, callback_data=RATING_STATS)],
        [InlineKeyboardButton(BUTTON_MONTH_WINNER, callback_data=WINNER_MONTH)],
        [InlineKeyboardButton(BUTTON_TOKEN_USAGE, callback_data=TOKEN_USAGE)],
        [
            InlineKeyboardButton(BUTTON_OWNER_HUSBAND, callback_data=OWNER_HUSBAND),
            InlineKeyboardButton(BUTTON_OWNER_WIFE, callback_data=OWNER_WIFE),
        ],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)


def get_help_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(BUTTON_COMMANDS, callback_data=HELP)],
        [InlineKeyboardButton(BUTTON_OFFLINE_MODE, callback_data=OFFLINE_HELP)],
        _back_button(),
    ]
    return InlineKeyboardMarkup(keyboard)
