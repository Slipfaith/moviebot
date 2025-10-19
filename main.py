from bot.setup_bot import create_bot

if __name__ == "__main__":
    app = create_bot()
    print("🎬 MovieBot запущен! (Ctrl+C для выхода)")
    app.run_polling()
