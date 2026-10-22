"""SideQuest's field-journal visual language and original vector components."""
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal as Signal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath
from PyQt6.QtWidgets import QLabel, QPushButton, QFrame, QWidget, QVBoxLayout, QHBoxLayout, QProgressBar

PAPER = '#f3f0e6'
INK = '#24392e'
GREEN = '#cddd9d'
MUTED = '#6d796c'
COLORS = {'Fern': '#d7e3bc', 'Apricot': '#efd2b8', 'Lilac': '#e1d7ec', 'Sky': '#cbdfe1', 'Rose': '#ebcfd0'}
STYLE = '''
QWidget { color: #24392e; font-family: "Segoe UI"; font-size: 13px; }
QMainWindow, QWidget#root { background: #f3f0e6; }
QFrame#rail { background: #233b30; }
QLabel#brand { color: #f6f4e9; font-size: 26px; font-weight: 700; letter-spacing: -1px; }
QLabel#railText { color: #b3c5b3; font-size: 11px; }
QLabel#railMicro { color: #b9cead; font-size: 10px; letter-spacing: 1px; }
QLabel#micro { color: #71816b; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#title { font-family: Georgia; font-size: 29px; }
QLabel#section { font-size: 18px; font-weight: 600; }
QLabel#muted { color: #6d796c; }
QFrame#card { background: #fffcf4; border: 1px solid #d7ddcc; border-radius: 14px; }
QFrame#card:hover { border-color: #91a878; }
QFrame#panel { background: #fffcf4; border: 1px solid #d7ddcc; border-radius: 14px; }
QFrame#stat { background: #e8edda; border: 1px solid #d5ddc4; border-radius: 12px; }
QLabel#value { font-size: 24px; font-weight: 700; color: #365337; }
QLabel#notice { background: #e6eddb; color: #365337; border: 1px solid #cbd7b9; border-radius: 9px; padding: 10px 14px; }
QLabel#notice[error="true"] { background: #f4ded6; border-color: #dba88f; color: #833f29; }
QPushButton { background: #fffdf5; border: 1px solid #cbd3c1; border-radius: 8px; padding: 10px 14px; font-weight: 600; }
QPushButton:hover { background: #e7edda; border-color: #829d69; }
QPushButton:pressed { background: #d2dfb8; }
QPushButton:disabled { color: #a5ac9d; background: #edece4; border-color: #dedfd4; }
QPushButton#primary { color: #20352a; background: #cddd9d; border-color: #b0c47b; }
QPushButton#primary:hover { background: #b8d17f; }
QPushButton#danger { color: #9b4a36; background: #f5e4dc; border-color: #e0b5a4; }
QPushButton#nav { background: transparent; color: #d0ddcc; border: none; text-align: left; padding: 12px 15px; }
QPushButton#nav:hover { background: #344e3e; }
QPushButton#nav:checked { background: #cddd9d; color: #20372a; }
QPushButton#small { padding: 6px 10px; font-size: 11px; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {
 background: #fffef9; border: 1px solid #cdd5c3; border-radius: 7px; padding: 9px; selection-background-color: #cddd9d;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #739450; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #fffdf5; color: #24392e; selection-background-color: #d9e5bf; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #93a47d; border-radius: 4px; background: #fffcf4; }
QCheckBox::indicator:checked { background: #627e44; border: 3px solid #bdcf9c; }
QProgressBar { background: #e4e9d9; border: none; border-radius: 4px; height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #658647; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #eeeede; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: #b4c19f; min-height: 26px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QTableWidget { background: #fffdf6; alternate-background-color: #eff2e7; gridline-color: #e1e6d7; border: 1px solid #d2dac7; border-radius: 9px; selection-background-color: #d7e5b9; selection-color: #213629; }
QHeaderView::section { background: #e8eddd; padding: 10px; border: none; color: #52664a; font-weight: 600; }
QTableWidget::item { padding: 6px; }
QMessageBox, QDialog, QCalendarWidget { background: #f3f0e6; }
'''


def label(value, name=None, wrap=False):
    item = QLabel(value)
    item.setWordWrap(wrap)
    if name:
        item.setObjectName(name)
    return item


def button(value, callback, name=None):
    item = QPushButton(value)
    item.clicked.connect(callback)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    if name:
        item.setObjectName(name)
    return item


def panel():
    item = QFrame()
    item.setObjectName('panel')
    return item


def stat(value, caption):
    item = QFrame()
    item.setObjectName('stat')
    layout = QVBoxLayout(item)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.addWidget(label(str(value), 'value'))
    layout.addWidget(label(caption.upper(), 'micro', True))
    return item


def heading(layout, eyebrow, title, subtitle):
    layout.addWidget(label(eyebrow.upper(), 'micro'))
    layout.addWidget(label(title, 'title', True))
    layout.addWidget(label(subtitle, 'muted', True))
    layout.addSpacing(10)


class TrailHero(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(194)
        self.setMaximumHeight(210)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#e0e9ca'))
        p.drawRoundedRect(QRectF(self.rect()), 17, 17)
        p.setPen(QColor('#5f7750'))
        p.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
        p.drawText(27, 31, 'YOUR FIELD GUIDE TO A MORE INTERESTING LIFE')
        p.setFont(QFont('Georgia', 27))
        p.setPen(QColor(INK))
        p.drawText(25, 79, 'Take the scenic route.')
        p.setFont(QFont('Segoe UI', 10))
        p.drawText(28, 112, 'A small adventure. A new skill. Something just for you.')
        p.setFont(QFont('Segoe UI', 9))
        p.setPen(QColor('#5d7152'))
        p.drawText(28, 163, 'LESS SOMEDAY. MORE TODAY.   ↗')
        if self.width() > 810:
            x = self.width()-220
            for i in range(7):
                p.setPen(QPen(QColor('#bdcca5'), 1))
                p.drawEllipse(QPointF(x+110, 80), 40+i*15, 27+i*10)
            path = QPainterPath(QPointF(x, 151))
            path.cubicTo(x+110, 160, x+2, 26, x+159, 49)
            p.setPen(QPen(QColor('#57734b'), 3, Qt.PenStyle.DashLine))
            p.drawPath(path)
            for px, py in [(x, 151), (x+58, 92), (x+159, 49)]:
                p.setPen(QPen(QColor('#648045'), 2))
                p.setBrush(QColor('#f3f0e6'))
                p.drawEllipse(QPointF(px, py), 7, 7)


class QuestCard(QFrame):
    chosen = Signal(int)

    def __init__(self, quest):
        super().__init__()
        self.setObjectName('card')
        self.setMinimumWidth(255)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(11)
        top = QHBoxLayout()
        chip = label((quest.get('collection_name') or 'UNFILED').upper())
        color = COLORS.get(quest.get('collection_color'), '#e4e8d9')
        chip.setStyleSheet(f'background: {color}; border-radius: 5px; padding: 5px 8px; font-size: 10px; font-weight: 600;')
        top.addWidget(chip)
        top.addStretch()
        top.addWidget(label(f"{quest['id']:02}", 'micro'))
        layout.addLayout(top)
        title = label(quest['title'], 'section', True)
        title.setMinimumHeight(48)
        layout.addWidget(title)
        description = label((quest['description'] or 'A little adventure waiting for its first step.')[:130], 'muted', True)
        description.setMinimumHeight(48)
        layout.addWidget(description)
        steps = quest['steps']
        completed = sum(s['done'] for s in steps)
        progress = QProgressBar()
        progress.setTextVisible(False)
        progress.setValue(round(completed/len(steps)*100) if steps else (100 if quest['status']=='Completed' else 0))
        layout.addWidget(progress)
        layout.addWidget(label(f'{completed}/{len(steps)} steps · '+quest['status'] if steps else quest['status'], 'micro'))
        footer = QHBoxLayout()
        footer.addWidget(label(quest['energy']+' energy', 'muted'))
        footer.addStretch()
        footer.addWidget(button('Open quest  ↗', lambda: self.chosen.emit(quest['id']), 'small'))
        layout.addLayout(footer)


class BarChart(QWidget):
    def __init__(self, title, items, color='#7f9d5a'):
        super().__init__()
        self.title, self.items, self.color = title, items, color
        self.setMinimumHeight(max(190, 65+len(items)*40))
        self.setMinimumWidth(280)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(INK))
        p.setFont(QFont('Segoe UI', 12, QFont.Weight.DemiBold))
        p.drawText(17, 30, self.title)
        largest = max((value for _, value in self.items), default=1) or 1
        for i, (caption, value) in enumerate(self.items):
            y = 58+i*40
            p.setFont(QFont('Segoe UI', 9))
            p.setPen(QColor(MUTED))
            p.drawText(17, y, caption[:24])
            p.drawText(self.width()-45, y, str(value))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#e3e9d6'))
            p.drawRoundedRect(QRectF(17, y+8, self.width()-45, 8), 4, 4)
            p.setBrush(QColor(self.color))
            if value:
                p.drawRoundedRect(QRectF(17, y+8, (self.width()-45)*value/largest, 8), 4, 4)
