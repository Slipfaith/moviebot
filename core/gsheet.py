import gspread
from datetime import datetime
from core.config import GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS

def connect_to_sheet():
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS)
    sh = gc.open(GOOGLE_SHEET_NAME)
    return sh.sheet1

def add_movie_row(worksheet, film, year, genre, rating, comment):
    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        film,
        year,
        genre,
        rating,
        comment
    ])
