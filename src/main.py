import sys

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


def main() -> int:
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("PyQt6 Hello World")

    layout = QVBoxLayout()
    label = QLabel("Hello, World!")
    layout.addWidget(label)
    window.setLayout(layout)

    window.resize(300, 100)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
