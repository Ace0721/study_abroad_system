from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.permission_service import PermissionService
from services.log_service import LogService
from ui.change_password_dialog import ChangePasswordDialog
from ui.tabs import (
    AgentCreateTab,
    AgentFeedbackTab,
    AgentListTab,
    ReviewerHistoryTab,
    ReviewerPendingTab,
    SchoolHistoryTab,
    SchoolPendingTab,
    SchoolQuotaTab,
)


class MainWindow(QMainWindow):
    def __init__(self, session_factory, app_session, on_logout) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.app_session = app_session
        self.on_logout = on_logout
        self.user_ctx = app_session.current_user
        self._logout_handled = False

        self.setWindowTitle("留学申请与审核系统")
        self.resize(1200, 760)
        self._build_ui()
        self._build_menu()

    def _build_ui(self) -> None:
        center = QWidget()
        layout = QVBoxLayout(center)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        school_name = self.user_ctx.university_name if self.user_ctx.university_name else "-"
        header_layout.addWidget(QLabel(f"当前用户：{self.user_ctx.full_name}"))
        header_layout.addWidget(QLabel(f"角色：{self.user_ctx.role_name}（{self.user_ctx.role_code}）"))
        header_layout.addWidget(QLabel(f"所属学校：{school_name}"))
        header_layout.addStretch(1)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self._load_tabs_by_role()
        layout.addWidget(self.tabs)
        self.setCentralWidget(center)

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        account_menu = QMenu("账户", self)
        menu_bar.addMenu(account_menu)

        change_password_action = QAction("修改密码", self)
        logout_action = QAction("退出登录", self)
        account_menu.addAction(change_password_action)
        account_menu.addAction(logout_action)

        change_password_action.triggered.connect(self._open_change_password_dialog)
        logout_action.triggered.connect(self._logout)

    def _load_tabs_by_role(self) -> None:
        role_code = self.user_ctx.role_code
        if PermissionService.is_agent(role_code):
            self.tabs.addTab(AgentCreateTab(self.session_factory, self.user_ctx), "申请录入")
            self.tabs.addTab(AgentListTab(self.session_factory, self.user_ctx), "我的申请")
            self.tabs.addTab(AgentFeedbackTab(self.session_factory, self.user_ctx), "反馈后处理")
            return

        if PermissionService.is_reviewer(role_code):
            self.tabs.addTab(ReviewerPendingTab(self.session_factory, self.user_ctx), "待审申请")
            self.tabs.addTab(ReviewerHistoryTab(self.session_factory, self.user_ctx), "审核历史")
            return

        if PermissionService.is_school_officer(role_code):
            self.tabs.addTab(SchoolPendingTab(self.session_factory, self.user_ctx), "学校待处理")
            self.tabs.addTab(SchoolQuotaTab(self.session_factory, self.user_ctx), "名额看板")
            self.tabs.addTab(SchoolHistoryTab(self.session_factory, self.user_ctx), "学校历史")
            return

        self.tabs.addTab(QWidget(), "未定义角色")

    def _open_change_password_dialog(self) -> None:
        dialog = ChangePasswordDialog(self.session_factory, self.user_ctx, self)
        dialog.exec()

    def _logout(self) -> None:
        if self._logout_handled:
            return
        with self.session_factory() as session:
            LogService(session).log_operation(
                user_id=self.user_ctx.user_id,
                operation_type="LOGOUT",
                operation_desc=f"User {self.user_ctx.username} logged out.",
            )
        self._logout_handled = True
        self.app_session.logout()
        self.close()
        self.on_logout()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._logout_handled and self.app_session.is_authenticated:
            with self.session_factory() as session:
                LogService(session).log_operation(
                    user_id=self.user_ctx.user_id,
                    operation_type="WINDOW_CLOSE_LOGOUT",
                    operation_desc=f"User {self.user_ctx.username} closed main window.",
                )
            self._logout_handled = True
            self.app_session.logout()
            self.on_logout()
        event.accept()
