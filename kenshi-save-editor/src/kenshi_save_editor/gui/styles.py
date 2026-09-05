APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #191713;
    color: #e9dfcf;
    font-family: "Segoe UI";
    font-size: 10.5pt;
}

QLabel {
    color: #f0e4d0;
}

QToolBar {
    background: #242018;
    border-bottom: 1px solid #4a4032;
    spacing: 8px;
    padding: 6px;
}

QPushButton {
    background: #5a4630;
    color: #f6ead8;
    border: 1px solid #8b7352;
    border-radius: 4px;
    padding: 6px 12px;
}

QPushButton:hover {
    background: #70583b;
}

QTreeWidget, QTableWidget {
    background: #211d17;
    alternate-background-color: #2a251d;
    border: 1px solid #4a4032;
    gridline-color: #4a4032;
    selection-background-color: #80613c;
    selection-color: #fff4df;
}

QHeaderView::section {
    background: #342d22;
    color: #f0e4d0;
    border: 0;
    border-right: 1px solid #4a4032;
    border-bottom: 1px solid #4a4032;
    padding: 5px;
}

QStatusBar {
    background: #242018;
    color: #d8c7ae;
}
"""
