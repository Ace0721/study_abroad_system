import logging

from PySide6.QtWidgets import QMessageBox, QWidget


def show_success(parent: QWidget, message: str) -> None:
    logging.info(message)
    QMessageBox.information(parent, "Success", message)


def show_warning(parent: QWidget, message: str) -> None:
    logging.warning(message)
    QMessageBox.warning(parent, "Warning", message)


def show_error(parent: QWidget, message: str) -> None:
    logging.error(message)
    QMessageBox.critical(parent, "Error", message)
