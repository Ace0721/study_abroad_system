from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.application_service import ApplicationService
from services.base_data_service import BaseDataService
from services.review_service import ReviewService
from services.school_service import SchoolService
from utils.enums import ApplicationStatus
from utils.exceptions import BusinessRuleError, ServiceNotReadyError
from utils.messages import show_error, show_success, show_warning


def _set_table_headers(table: QTableWidget, headers: list[str]) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)


def _status_values() -> list[str]:
    return [s.value for s in ApplicationStatus]


STATUS_LABELS = {
    ApplicationStatus.SUBMITTED.value: "已提交",
    ApplicationStatus.REVIEW_REJECTED.value: "审核不通过",
    ApplicationStatus.SCHOOL_PENDING.value: "待学校处理",
    ApplicationStatus.SCHOOL_FEEDBACK.value: "学校反馈",
    ApplicationStatus.SCHOOL_RESERVED.value: "学校已占位",
    ApplicationStatus.CANCELLED.value: "已撤销",
    ApplicationStatus.CLOSED.value: "已关闭",
}


def _status_label(status_code: str | None) -> str:
    if not status_code:
        return "-"
    return STATUS_LABELS.get(status_code, status_code)


def _set_status_filter_value(combo: QComboBox, status_code: str) -> None:
    index = combo.findData(status_code)
    if index >= 0:
        combo.setCurrentIndex(index)


def _major_display(major) -> str:
    return f"{major.major_name}({major.major_code})"


def _create_readonly_line() -> QLineEdit:
    widget = QLineEdit()
    widget.setReadOnly(True)
    return widget


def _create_readonly_text() -> QTextEdit:
    widget = QTextEdit()
    widget.setReadOnly(True)
    widget.setMinimumHeight(70)
    return widget


class BaseStatusTableTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", "")
        for status in _status_values():
            self.status_filter.addItem(_status_label(status), status)
        self.refresh_button = QPushButton("刷新")

    def build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("状态筛选"))
        row.addWidget(self.status_filter)
        row.addStretch(1)
        row.addWidget(self.refresh_button)
        return row


class AgentCreateTab(QWidget):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self.university_combo = QComboBox()
        self.major_combo = QComboBox()
        self._build_ui()
        self._load_universities()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.student_code_edit = QLineEdit()
        self.student_name_edit = QLineEdit()
        self.current_school_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.self_statement_edit = QTextEdit()
        self.transcript_path_edit = QLineEdit()

        form.addRow("学生编号", self.student_code_edit)
        form.addRow("学生姓名", self.student_name_edit)
        form.addRow("在读学校", self.current_school_edit)
        form.addRow("邮箱", self.email_edit)
        form.addRow("电话", self.phone_edit)
        form.addRow("申请学校", self.university_combo)
        form.addRow("申请专业", self.major_combo)
        form.addRow("自荐材料", self.self_statement_edit)
        form.addRow("成绩单路径", self.transcript_path_edit)

        self.submit_button = QPushButton("创建并提交申请")
        self.submit_button.clicked.connect(self._on_submit_clicked)
        self.university_combo.currentIndexChanged.connect(self._on_university_changed)

        layout.addLayout(form)
        layout.addWidget(self.submit_button, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_universities(self) -> None:
        self.university_combo.clear()
        with self.session_factory() as session:
            universities = BaseDataService(session).list_universities()
            for uni in universities:
                self.university_combo.addItem(uni.university_name, uni.id)
        self._on_university_changed()

    def _on_university_changed(self) -> None:
        self.major_combo.clear()
        university_id = self.university_combo.currentData()
        if not university_id:
            return
        with self.session_factory() as session:
            majors = SchoolService(session).list_majors_by_university(university_id)
            for major in majors:
                self.major_combo.addItem(_major_display(major), major.id)

    def _on_submit_clicked(self) -> None:
        payload = {
            "agent_user_id": self.user_ctx.user_id,
            "student_code": self.student_code_edit.text().strip(),
            "student_name": self.student_name_edit.text().strip(),
            "current_school": self.current_school_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "university_id": self.university_combo.currentData(),
            "major_id": self.major_combo.currentData(),
            "self_statement": self.self_statement_edit.toPlainText().strip(),
            "transcript_path": self.transcript_path_edit.text().strip(),
        }
        with self.session_factory() as session:
            service = ApplicationService(session)
            try:
                service.create_and_submit_application(payload)
                show_success(self, "申请提交成功。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"提交失败：{exc}")


class AgentListTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addLayout(self.build_filter_row())

        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "申请学校ID", "申请专业ID", "状态", "更新时间"],
        )
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.detail_button = QPushButton("查看详情")
        self.cancel_button = QPushButton("撤销申请")
        self.feedback_button = QPushButton("查看反馈")
        row.addStretch(1)
        row.addWidget(self.detail_button)
        row.addWidget(self.cancel_button)
        row.addWidget(self.feedback_button)
        layout.addLayout(row)

        self.detail_button.clicked.connect(self._show_detail)
        self.cancel_button.clicked.connect(self._cancel_application)
        self.feedback_button.clicked.connect(self._show_feedback)

    def _selected_application_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def refresh_table(self) -> None:
        status = self.status_filter.currentData()
        with self.session_factory() as session:
            apps = ApplicationService(session).list_by_agent(self.user_ctx.user_id, status=status)
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.university_id)))
            self.table.setItem(i, 5, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 6, QTableWidgetItem(_status_label(app.status)))
            self.table.setItem(i, 7, QTableWidgetItem(app.updated_at.strftime("%Y-%m-%d %H:%M:%S")))

    def _show_detail(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        show_success(self, f"申请详情查看入口已就绪（申请ID={app_id}）。")

    def _cancel_application(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        with self.session_factory() as session:
            service = ApplicationService(session)
            try:
                service.cancel_application(app_id, self.user_ctx.user_id)
                show_success(self, "申请已撤销。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"撤销失败：{exc}")
        self.refresh_table()

    def _show_feedback(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        with self.session_factory() as session:
            feedback = SchoolService(session).get_feedback(app_id)
            if not feedback:
                show_warning(self, "当前申请暂无反馈记录。")
                return
            show_success(self, f"反馈内容：{feedback.feedback_content}")


class AgentFeedbackTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.transfer_university_combo.currentIndexChanged.connect(self._on_transfer_university_changed)
        self.table.itemSelectionChanged.connect(self._load_feedback_detail)
        self.refresh_table()
        self._load_transfer_universities()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        _set_status_filter_value(self.status_filter, ApplicationStatus.SCHOOL_FEEDBACK.value)
        self.status_filter.setEnabled(False)
        layout.addLayout(self.build_filter_row())

        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "原申请学校ID", "原申请专业ID", "状态"],
        )
        layout.addWidget(self.table)

        feedback_box = QGroupBox("学校反馈信息（只读）")
        feedback_layout = QFormLayout(feedback_box)
        self.feedback_content_view = QTextEdit()
        self.feedback_content_view.setReadOnly(True)
        self.suggested_major_view = QLineEdit()
        self.suggested_major_view.setReadOnly(True)
        feedback_layout.addRow("反馈内容", self.feedback_content_view)
        feedback_layout.addRow("建议专业", self.suggested_major_view)
        layout.addWidget(feedback_box)

        action_box = QGroupBox("反馈后处理动作")
        action_layout = QGridLayout(action_box)
        self.new_major_combo = QComboBox()
        self.transfer_university_combo = QComboBox()
        self.transfer_major_combo = QComboBox()
        self.resubmit_major_button = QPushButton("改专业重申")
        self.transfer_button = QPushButton("跨校转申")

        action_layout.addWidget(QLabel("同校新专业"), 0, 0)
        action_layout.addWidget(self.new_major_combo, 0, 1)
        action_layout.addWidget(self.resubmit_major_button, 0, 2)
        action_layout.addWidget(QLabel("新学校"), 1, 0)
        action_layout.addWidget(self.transfer_university_combo, 1, 1)
        action_layout.addWidget(QLabel("新专业"), 2, 0)
        action_layout.addWidget(self.transfer_major_combo, 2, 1)
        action_layout.addWidget(self.transfer_button, 2, 2)
        layout.addWidget(action_box)

        self.resubmit_major_button.clicked.connect(self._resubmit_major)
        self.transfer_button.clicked.connect(self._transfer)

    def _selected_application_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _selected_university_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 4).text())

    def refresh_table(self) -> None:
        with self.session_factory() as session:
            apps = ApplicationService(session).list_feedback_queue(self.user_ctx.user_id)
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.university_id)))
            self.table.setItem(i, 5, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 6, QTableWidgetItem(_status_label(app.status)))
        if apps:
            self.table.selectRow(0)
            self._load_feedback_detail()
        else:
            self.feedback_content_view.clear()
            self.suggested_major_view.clear()
            self.new_major_combo.clear()

    def _load_feedback_detail(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            self.feedback_content_view.clear()
            self.suggested_major_view.clear()
            return

        with self.session_factory() as session:
            school_service = SchoolService(session)
            feedback = school_service.get_feedback(app_id)
            if feedback:
                self.feedback_content_view.setPlainText(feedback.feedback_content)
                suggested_text = "-"
                current_uni_id = self._selected_university_id()
                if feedback.suggested_major_id and current_uni_id:
                    majors = school_service.list_majors_by_university(current_uni_id)
                    major_map = {major.id: _major_display(major) for major in majors}
                    suggested_text = major_map.get(feedback.suggested_major_id, str(feedback.suggested_major_id))
                self.suggested_major_view.setText(suggested_text)
            else:
                self.feedback_content_view.setPlainText("暂无反馈")
                self.suggested_major_view.setText("-")

            self.new_major_combo.clear()
            current_uni_id = self._selected_university_id()
            if current_uni_id:
                majors = school_service.list_majors_by_university(current_uni_id)
                for major in majors:
                    self.new_major_combo.addItem(_major_display(major), major.id)

    def _load_transfer_universities(self) -> None:
        self.transfer_university_combo.clear()
        with self.session_factory() as session:
            universities = BaseDataService(session).list_universities()
            for uni in universities:
                self.transfer_university_combo.addItem(uni.university_name, uni.id)
        self._on_transfer_university_changed()

    def _on_transfer_university_changed(self) -> None:
        self.transfer_major_combo.clear()
        target_uni_id = self.transfer_university_combo.currentData()
        if not target_uni_id:
            return
        with self.session_factory() as session:
            majors = SchoolService(session).list_majors_by_university(target_uni_id)
            for major in majors:
                self.transfer_major_combo.addItem(_major_display(major), major.id)

    def _resubmit_major(self) -> None:
        app_id = self._selected_application_id()
        new_major_id = self.new_major_combo.currentData()
        if not app_id or not new_major_id:
            show_warning(self, "请先选择反馈申请和目标专业。")
            return
        with self.session_factory() as session:
            service = ApplicationService(session)
            try:
                service.resubmit_with_new_major(app_id, new_major_id, self.user_ctx.user_id)
                show_success(self, "已发起改专业重申。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"处理失败：{exc}")
        self.refresh_table()

    def _transfer(self) -> None:
        app_id = self._selected_application_id()
        new_uni_id = self.transfer_university_combo.currentData()
        new_major_id = self.transfer_major_combo.currentData()
        if not app_id or not new_uni_id or not new_major_id:
            show_warning(self, "请完整选择新学校和新专业。")
            return
        with self.session_factory() as session:
            service = ApplicationService(session)
            try:
                service.transfer_to_other_university(
                    app_id,
                    new_uni_id,
                    new_major_id,
                    self.user_ctx.user_id,
                )
                show_success(self, "已发起跨校转申。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"处理失败：{exc}")
        self.refresh_table()


class ReviewerPendingTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        _set_status_filter_value(self.status_filter, ApplicationStatus.SUBMITTED.value)
        layout.addLayout(self.build_filter_row())

        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "申请学校ID", "申请专业ID", "状态"],
        )
        layout.addWidget(self.table)

        self.review_comment_edit = QTextEdit()
        self.review_comment_edit.setPlaceholderText("审核意见（不通过必填，通过可选）")
        layout.addWidget(self.review_comment_edit)

        row = QHBoxLayout()
        self.approve_button = QPushButton("审核通过")
        self.reject_button = QPushButton("审核不通过")
        row.addStretch(1)
        row.addWidget(self.approve_button)
        row.addWidget(self.reject_button)
        layout.addLayout(row)

        self.approve_button.clicked.connect(self._approve)
        self.reject_button.clicked.connect(self._reject)

    def _selected_application_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def refresh_table(self) -> None:
        status = self.status_filter.currentData()
        with self.session_factory() as session:
            apps = ReviewService(session).list_submitted(status=status)
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.university_id)))
            self.table.setItem(i, 5, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 6, QTableWidgetItem(_status_label(app.status)))

    def _approve(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        comment = self.review_comment_edit.toPlainText().strip()
        with self.session_factory() as session:
            service = ReviewService(session)
            try:
                service.approve(app_id, self.user_ctx.user_id, comment)
                show_success(self, "审核通过。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"审核失败：{exc}")
        self.refresh_table()

    def _reject(self) -> None:
        app_id = self._selected_application_id()
        comment = self.review_comment_edit.toPlainText().strip()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        if not comment:
            show_warning(self, "审核不通过时，审核意见为必填。")
            return
        with self.session_factory() as session:
            service = ReviewService(session)
            try:
                service.reject(app_id, self.user_ctx.user_id, comment)
                show_success(self, "已审核不通过。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"审核失败：{exc}")
        self.refresh_table()


class ReviewerHistoryTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addLayout(self.build_filter_row())
        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "申请学校ID", "申请专业ID", "状态", "更新时间"],
        )
        layout.addWidget(self.table)

    def refresh_table(self) -> None:
        status = self.status_filter.currentData()
        with self.session_factory() as session:
            apps = ReviewService(session).list_history(self.user_ctx.user_id, status=status)
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.university_id)))
            self.table.setItem(i, 5, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 6, QTableWidgetItem(_status_label(app.status)))
            self.table.setItem(i, 7, QTableWidgetItem(app.updated_at.strftime("%Y-%m-%d %H:%M:%S")))


class SchoolPendingTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        _set_status_filter_value(self.status_filter, ApplicationStatus.SCHOOL_PENDING.value)
        layout.addLayout(self.build_filter_row())

        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "申请专业ID", "状态"],
        )
        layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self._load_detail)

        detail_box = QGroupBox("申请详情（只读）")
        detail_layout = QFormLayout(detail_box)
        self.detail_application_no = _create_readonly_line()
        self.detail_student_name = _create_readonly_line()
        self.detail_current_school = _create_readonly_line()
        self.detail_email = _create_readonly_line()
        self.detail_university = _create_readonly_line()
        self.detail_major = _create_readonly_line()
        self.detail_status = _create_readonly_line()
        self.detail_transcript_path = _create_readonly_line()
        self.detail_review_comment = _create_readonly_text()
        self.detail_feedback_comment = _create_readonly_text()
        self.detail_self_statement = _create_readonly_text()
        detail_layout.addRow("申请编号", self.detail_application_no)
        detail_layout.addRow("学生姓名", self.detail_student_name)
        detail_layout.addRow("在读学校", self.detail_current_school)
        detail_layout.addRow("联系邮箱", self.detail_email)
        detail_layout.addRow("申请学校", self.detail_university)
        detail_layout.addRow("申请专业", self.detail_major)
        detail_layout.addRow("当前状态", self.detail_status)
        detail_layout.addRow("成绩单路径", self.detail_transcript_path)
        detail_layout.addRow("审核意见", self.detail_review_comment)
        detail_layout.addRow("学校反馈", self.detail_feedback_comment)
        detail_layout.addRow("自荐材料", self.detail_self_statement)
        layout.addWidget(detail_box)

        self.feedback_content_edit = QTextEdit()
        self.feedback_content_edit.setPlaceholderText("反馈内容（必填）")
        layout.addWidget(self.feedback_content_edit)

        feedback_row = QHBoxLayout()
        feedback_row.addWidget(QLabel("建议专业（可选，仅本校）"))
        self.suggested_major_combo = QComboBox()
        feedback_row.addWidget(self.suggested_major_combo)
        feedback_row.addStretch(1)
        layout.addLayout(feedback_row)

        row = QHBoxLayout()
        self.reserve_button = QPushButton("占位批准")
        self.feedback_button = QPushButton("反馈建议")
        row.addStretch(1)
        row.addWidget(self.reserve_button)
        row.addWidget(self.feedback_button)
        layout.addLayout(row)

        self.reserve_button.clicked.connect(self._reserve)
        self.feedback_button.clicked.connect(self._feedback)
        self._load_school_majors()

    def _load_school_majors(self) -> None:
        self.suggested_major_combo.clear()
        self.suggested_major_combo.addItem("不指定", None)
        if not self.user_ctx.university_id:
            return
        with self.session_factory() as session:
            majors = SchoolService(session).list_majors_by_university(self.user_ctx.university_id)
            for major in majors:
                self.suggested_major_combo.addItem(_major_display(major), major.id)

    def _selected_application_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def refresh_table(self) -> None:
        if not self.user_ctx.university_id:
            return
        status = self.status_filter.currentData()
        with self.session_factory() as session:
            apps = SchoolService(session).list_pending_for_school(
                self.user_ctx.university_id,
                status=status,
            )
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 5, QTableWidgetItem(_status_label(app.status)))
        if apps:
            self.table.selectRow(0)
            self._load_detail()
        else:
            self._clear_detail()

    def _load_detail(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            self._clear_detail()
            return

        with self.session_factory() as session:
            detail = SchoolService(session).get_application_detail_for_school(
                app_id,
                self.user_ctx.user_id,
            )

        app = detail["application"]
        major_text = detail["major_name"]
        if detail["major_code"]:
            major_text = f"{major_text}({detail['major_code']})"

        self.detail_application_no.setText(app.application_no)
        self.detail_student_name.setText(app.student_name_snapshot or "-")
        self.detail_current_school.setText(app.current_school_snapshot or "-")
        self.detail_email.setText(app.email_snapshot or "-")
        self.detail_university.setText(detail["university_name"] or "-")
        self.detail_major.setText(major_text or "-")
        self.detail_status.setText(_status_label(app.status))
        self.detail_transcript_path.setText(app.transcript_path or "-")
        self.detail_review_comment.setPlainText(app.review_comment or "-")
        self.detail_feedback_comment.setPlainText(app.school_comment or "-")
        self.detail_self_statement.setPlainText(app.self_statement or "-")

    def _clear_detail(self) -> None:
        self.detail_application_no.clear()
        self.detail_student_name.clear()
        self.detail_current_school.clear()
        self.detail_email.clear()
        self.detail_university.clear()
        self.detail_major.clear()
        self.detail_status.clear()
        self.detail_transcript_path.clear()
        self.detail_review_comment.clear()
        self.detail_feedback_comment.clear()
        self.detail_self_statement.clear()

    def _reserve(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        with self.session_factory() as session:
            service = SchoolService(session)
            try:
                service.reserve_slot(app_id, self.user_ctx.user_id)
                show_success(self, "占位批准成功。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"占位失败：{exc}")
        self.refresh_table()

    def _feedback(self) -> None:
        app_id = self._selected_application_id()
        content = self.feedback_content_edit.toPlainText().strip()
        suggested_major_id = self.suggested_major_combo.currentData()
        if not app_id:
            show_warning(self, "请先选择一条申请。")
            return
        if not content:
            show_warning(self, "学校反馈时，反馈内容为必填。")
            return
        with self.session_factory() as session:
            service = SchoolService(session)
            try:
                service.send_feedback(app_id, self.user_ctx.user_id, content, suggested_major_id)
                show_success(self, "反馈已提交。")
            except BusinessRuleError as exc:
                show_warning(self, str(exc))
            except ServiceNotReadyError as exc:
                show_warning(self, str(exc))
            except Exception as exc:
                show_error(self, f"反馈失败：{exc}")
        self.refresh_table()


class SchoolQuotaTab(QWidget):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        top_row = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.total_label = QLabel("学校总名额: -")
        self.used_label = QLabel("已用名额: -")
        self.left_label = QLabel("剩余名额: -")
        top_row.addWidget(self.total_label)
        top_row.addWidget(self.used_label)
        top_row.addWidget(self.left_label)
        top_row.addStretch(1)
        top_row.addWidget(self.refresh_button)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        _set_table_headers(self.table, ["专业ID", "专业代码", "专业名称", "总名额", "已用", "剩余"])
        layout.addWidget(self.table)

        self.refresh_button.clicked.connect(self.refresh_data)

    def refresh_data(self) -> None:
        if not self.user_ctx.university_id:
            return
        with self.session_factory() as session:
            data = SchoolService(session).get_quota_dashboard(self.user_ctx.university_id)
        uni = data["university"]
        majors = data["majors"]
        if not uni:
            return

        self.total_label.setText(f"学校总名额: {uni.total_quota}")
        self.used_label.setText(f"已用名额: {uni.used_quota}")
        self.left_label.setText(f"剩余名额: {uni.total_quota - uni.used_quota}")

        self.table.setRowCount(len(majors))
        for i, major in enumerate(majors):
            self.table.setItem(i, 0, QTableWidgetItem(str(major.id)))
            self.table.setItem(i, 1, QTableWidgetItem(major.major_code))
            self.table.setItem(i, 2, QTableWidgetItem(major.major_name))
            self.table.setItem(i, 3, QTableWidgetItem(str(major.major_quota)))
            self.table.setItem(i, 4, QTableWidgetItem(str(major.used_quota)))
            self.table.setItem(i, 5, QTableWidgetItem(str(major.major_quota - major.used_quota)))


class SchoolHistoryTab(BaseStatusTableTab):
    def __init__(self, session_factory, user_ctx) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_ctx = user_ctx
        self._build_ui()
        self.refresh_button.clicked.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addLayout(self.build_filter_row())
        self.table = QTableWidget()
        _set_table_headers(
            self.table,
            ["ID", "申请编号", "学生姓名", "在读学校", "申请专业ID", "状态", "更新时间"],
        )
        layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self._load_detail)

        detail_box = QGroupBox("申请详情（只读）")
        detail_layout = QFormLayout(detail_box)
        self.detail_application_no = _create_readonly_line()
        self.detail_student_name = _create_readonly_line()
        self.detail_current_school = _create_readonly_line()
        self.detail_email = _create_readonly_line()
        self.detail_university = _create_readonly_line()
        self.detail_major = _create_readonly_line()
        self.detail_status = _create_readonly_line()
        self.detail_transcript_path = _create_readonly_line()
        self.detail_review_comment = _create_readonly_text()
        self.detail_feedback_comment = _create_readonly_text()
        self.detail_self_statement = _create_readonly_text()
        detail_layout.addRow("申请编号", self.detail_application_no)
        detail_layout.addRow("学生姓名", self.detail_student_name)
        detail_layout.addRow("在读学校", self.detail_current_school)
        detail_layout.addRow("联系邮箱", self.detail_email)
        detail_layout.addRow("申请学校", self.detail_university)
        detail_layout.addRow("申请专业", self.detail_major)
        detail_layout.addRow("当前状态", self.detail_status)
        detail_layout.addRow("成绩单路径", self.detail_transcript_path)
        detail_layout.addRow("审核意见", self.detail_review_comment)
        detail_layout.addRow("学校反馈", self.detail_feedback_comment)
        detail_layout.addRow("自荐材料", self.detail_self_statement)
        layout.addWidget(detail_box)

    def refresh_table(self) -> None:
        if not self.user_ctx.university_id:
            return
        status = self.status_filter.currentData()
        with self.session_factory() as session:
            apps = SchoolService(session).list_school_history(self.user_ctx.university_id, status)
        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            self.table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self.table.setItem(i, 1, QTableWidgetItem(app.application_no))
            self.table.setItem(i, 2, QTableWidgetItem(app.student_name_snapshot))
            self.table.setItem(i, 3, QTableWidgetItem(app.current_school_snapshot))
            self.table.setItem(i, 4, QTableWidgetItem(str(app.major_id)))
            self.table.setItem(i, 5, QTableWidgetItem(_status_label(app.status)))
            self.table.setItem(i, 6, QTableWidgetItem(app.updated_at.strftime("%Y-%m-%d %H:%M:%S")))
        if apps:
            self.table.selectRow(0)
            self._load_detail()
        else:
            self._clear_detail()

    def _selected_application_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _load_detail(self) -> None:
        app_id = self._selected_application_id()
        if not app_id:
            self._clear_detail()
            return

        with self.session_factory() as session:
            detail = SchoolService(session).get_application_detail_for_school(
                app_id,
                self.user_ctx.user_id,
            )

        app = detail["application"]
        major_text = detail["major_name"]
        if detail["major_code"]:
            major_text = f"{major_text}({detail['major_code']})"

        self.detail_application_no.setText(app.application_no)
        self.detail_student_name.setText(app.student_name_snapshot or "-")
        self.detail_current_school.setText(app.current_school_snapshot or "-")
        self.detail_email.setText(app.email_snapshot or "-")
        self.detail_university.setText(detail["university_name"] or "-")
        self.detail_major.setText(major_text or "-")
        self.detail_status.setText(_status_label(app.status))
        self.detail_transcript_path.setText(app.transcript_path or "-")
        self.detail_review_comment.setPlainText(app.review_comment or "-")
        self.detail_feedback_comment.setPlainText(app.school_comment or "-")
        self.detail_self_statement.setPlainText(app.self_statement or "-")

    def _clear_detail(self) -> None:
        self.detail_application_no.clear()
        self.detail_student_name.clear()
        self.detail_current_school.clear()
        self.detail_email.clear()
        self.detail_university.clear()
        self.detail_major.clear()
        self.detail_status.clear()
        self.detail_transcript_path.clear()
        self.detail_review_comment.clear()
        self.detail_feedback_comment.clear()
        self.detail_self_statement.clear()
