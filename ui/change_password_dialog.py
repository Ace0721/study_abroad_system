from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from services.auth_service import AuthService
from utils.exceptions import BusinessRuleError
from utils.messages import show_success, show_warning


class ChangePasswordDialog(QDialog):
    def __init__(self, session_factory, user_ctx, parent=None) -> None:
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self.setWindowTitle("修改密码")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("原密码", self.old_password_edit)
        form.addRow("新密码", self.new_password_edit)
        form.addRow("确认新密码", self.confirm_password_edit)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.submit_button = QPushButton("提交")
        self.cancel_button = QPushButton("取消")
        buttons.addStretch(1)
        buttons.addWidget(self.submit_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.submit_button.clicked.connect(self._on_submit)
        self.cancel_button.clicked.connect(self.reject)

    def _on_submit(self) -> None:
        old_password = self.old_password_edit.text().strip()
        new_password = self.new_password_edit.text().strip()
        confirm_password = self.confirm_password_edit.text().strip()

        if not old_password or not new_password or not confirm_password:
            show_warning(self, "请完整填写密码项。")
            return
        if new_password != confirm_password:
            show_warning(self, "两次输入的新密码不一致。")
            return
        if len(new_password) < 6:
            show_warning(self, "新密码至少 6 位。")
            return
        if new_password == old_password:
            show_warning(self, "新密码不能与原密码相同。")
            return

        try:
            with self.session_factory() as session:
                ok = AuthService(session).change_password(
                    self.user_ctx.user_id,
                    old_password,
                    new_password,
                )
        except BusinessRuleError as exc:
            show_warning(self, str(exc))
            return
        if not ok:
            show_warning(self, "原密码错误。")
            return
        show_success(self, "密码修改成功。")
        self.accept()
