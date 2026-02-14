from bot.setup_bot import create_bot
from core.config import STARTUP_CHECK_SHEET
from core.diagnostics import print_startup_diagnostics

if __name__ == "__main__":
    print_startup_diagnostics(check_sheet=STARTUP_CHECK_SHEET)
    app = create_bot()
    print("🎬 MovieBot запущен! (Ctrl+C для выхода)")
    app.run_polling()
