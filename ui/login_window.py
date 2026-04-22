from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.auth_service import AuthService
from ui.main_window import MainWindow
from utils.messages import show_error, show_warning


class LoginWindow(QWidget):
    def __init__(self, session_factory, app_session) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.app_session = app_session
        self.main_window: MainWindow | None = None

        self.setWindowTitle("留学申请与审核系统 - 登录")
        self.setFixedSize(420, 260)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        title = QLabel("留学申请与审核系统")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("密码")

        layout.addWidget(self.username_edit)
        layout.addWidget(self.password_edit)

        row = QHBoxLayout()
        self.login_button = QPushButton("登录")
        self.exit_button = QPushButton("退出")
        row.addStretch(1)
        row.addWidget(self.login_button)
        row.addWidget(self.exit_button)
        layout.addLayout(row)

        self.login_button.clicked.connect(self._login)
        self.exit_button.clicked.connect(self.close)
        self.password_edit.returnPressed.connect(self._login)

    def _login(self) -> None:
        if self.app_session.is_authenticated:
            show_warning(self, "当前程序已存在登录会话。")
            return

        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            show_warning(self, "请输入用户名和密码。")
            return

        with self.session_factory() as session:
            auth_service = AuthService(session)
            try:
                user_ctx = auth_service.login(username, password)
            except Exception as exc:
                show_error(self, f"登录失败：{exc}")
                return

        if not user_ctx:
            show_warning(self, "用户名或密码错误。")
            return

        try:
            self.app_session.login(user_ctx)
        except RuntimeError as exc:
            show_warning(self, str(exc))
            return

        self.main_window = MainWindow(
            session_factory=self.session_factory,
            app_session=self.app_session,
            on_logout=self._on_logout,
        )
        self.main_window.show()
        self.hide()

    def _on_logout(self) -> None:
        self.password_edit.clear()
        self.show()
