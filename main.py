import sys

from PySide6.QtWidgets import QApplication

from controllers.session_controller import AppSession
from database.db import SessionLocal
from database.init_db import initialize_database
from services.base_data_service import BaseDataService
from ui.login_window import LoginWindow
from utils.app_logger import configure_app_logger


def bootstrap() -> None:
    initialize_database()
    with SessionLocal() as session:
        BaseDataService(session).initialize_base_data()


def main() -> int:
    configure_app_logger()
    bootstrap()
    app = QApplication(sys.argv)
    app_session = AppSession()
    login_window = LoginWindow(session_factory=SessionLocal, app_session=app_session)
    login_window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
