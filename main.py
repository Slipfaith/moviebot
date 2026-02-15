import logging

from bot.setup_bot import create_bot
from core.config import STARTUP_CHECK_SHEET
from core.diagnostics import print_startup_diagnostics
from core.logging_setup import setup_logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    setup_logging()
    print_startup_diagnostics(check_sheet=STARTUP_CHECK_SHEET)
    app = create_bot()
    logger.info("MovieBot started (Ctrl+C to exit).")
    app.run_polling()
