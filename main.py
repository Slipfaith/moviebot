from bot.setup_bot import create_bot
from core.diagnostics import print_startup_diagnostics

if __name__ == "__main__":
    print_startup_diagnostics()
    app = create_bot()
    print("🎬 MovieBot запущен! (Ctrl+C для выхода)")
    app.run_polling()
