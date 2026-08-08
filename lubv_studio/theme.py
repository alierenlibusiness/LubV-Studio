"""Gorsel dil: renk paleti, Qt paleti ve butun uygulamanin QSS'i.

Siyah zemin uzerine tek bir vurgu rengi (yesil) kuruludur. Kirmizi ve amber
yalnizca durum bildirmek icin kullanilir; boylece ekran dagilmaz, butun
ogeler ayni aileye ait gorunur. Olculer (yaricap, bosluk) sabittir.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

C = {
    # zeminler: gercek siyahtan gri tonlarina
    "bg0": "#0A0A0B",     # ana tuval
    "bg1": "#0F1011",     # paneller, seritler
    "bg2": "#151617",     # kartlar, girisler
    "bg3": "#1C1E1F",     # hover
    "bg4": "#26292A",     # secili / basili
    "kod": "#08090A",     # kod ve terminal zemini

    # cizgiler
    "line": "#1A1C1D",
    "line2": "#26292B",
    "line3": "#383C3E",

    # yazi
    "text": "#F2F4F3",
    "text2": "#AFB5B3",
    "muted": "#71787A",

    # vurgu: yesil
    "accent": "#53FC18",
    "accent_hi": "#6FFF3E",
    "accent_lo": "#00E701",
    "accent_dim": "#12240A",
    "accent_soft": "#1B3312",
    "violet": "#53FC18",      # LUBV kimligi
    "violet_dim": "#12240A",

    # durum
    "green": "#53FC18",
    "green_dim": "#12240A",
    "red": "#FF4A4A",
    "red_dim": "#2E1414",
    "amber": "#FFB020",
    "amber_dim": "#2E2210",
    "cyan": "#C9D1CE",        # plan modu: notr
    "cyan_dim": "#1F2422",
}

# yesil gradyan: birincil dugmeler ve vurgular icin
GRADYAN = (
    "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
    "stop:0 #53FC18, stop:1 #00E701)"
)
GRADYAN_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
    "stop:0 #6FFF3E, stop:1 #15F51A)"
)

UI_FONT = "Segoe UI"
CODE_FONT = "Cascadia Mono, Consolas, monospace"

# olculer: her yerde ayni degerler kullanilir
R_KUCUK = 6
R_ORTA = 8
R_BUYUK = 10


def palette() -> QPalette:
    """Fusion'in beyaz varsayilanlarini komple koyuya cevirir.

    Bu olmadan QScrollArea, QListView gibi widget'larin ic zeminleri beyaz kalir.
    """
    p = QPalette()
    zemin = QColor(C["bg0"])
    panel = QColor(C["bg2"])
    yazi = QColor(C["text"])
    sonuk = QColor(C["muted"])

    p.setColor(QPalette.ColorRole.Window, zemin)
    p.setColor(QPalette.ColorRole.WindowText, yazi)
    p.setColor(QPalette.ColorRole.Base, panel)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(C["bg1"]))
    p.setColor(QPalette.ColorRole.Text, yazi)
    p.setColor(QPalette.ColorRole.Button, QColor(C["bg2"]))
    p.setColor(QPalette.ColorRole.ButtonText, yazi)
    p.setColor(QPalette.ColorRole.BrightText, QColor(C["red"]))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(C["bg4"]))
    p.setColor(QPalette.ColorRole.ToolTipText, yazi)
    p.setColor(QPalette.ColorRole.Highlight, QColor(C["accent"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#06140A"))
    p.setColor(QPalette.ColorRole.Link, QColor(C["accent_hi"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, sonuk)

    for durum in (QPalette.ColorGroup.Disabled,):
        p.setColor(durum, QPalette.ColorRole.Text, sonuk)
        p.setColor(durum, QPalette.ColorRole.ButtonText, sonuk)
        p.setColor(durum, QPalette.ColorRole.WindowText, sonuk)
    return p


def qss() -> str:
    return f"""
/* ============ temel ============ */
QWidget {{
    font-family: "{UI_FONT}", sans-serif;
    font-size: 13px;
    color: {C['text']};
    background: transparent;
}}
QMainWindow, QWidget#Root {{ background: {C['bg0']}; }}
QDialog {{ background: {C['bg1']}; }}
QToolTip {{
    background: {C['bg4']};
    color: {C['text']};
    border: 1px solid {C['line2']};
    border-radius: {R_KUCUK}px;
    padding: 5px 8px;
}}

/* ============ sol ikon rayi ============ */
QFrame#Rail {{
    background: {C['bg1']};
    border-right: 1px solid {C['line']};
}}
QToolButton#RailButton {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
}}
QToolButton#RailButton:hover {{ background: {C['bg3']}; }}
QToolButton#RailButton:checked {{
    background: {C['bg3']};
    border-left: 2px solid {C['accent']};
}}

/* ============ paneller ============ */
QFrame#SidePanel {{
    background: {C['bg1']};
    border-right: 1px solid {C['line']};
}}
QFrame#PanelHeader {{
    background: {C['bg1']};
    border-bottom: 1px solid {C['line']};
}}
QLabel#PanelTitle {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {C['text2']};
}}
QLabel#PanelHint {{ color: {C['muted']}; font-size: 11.5px; }}
QLabel#SectionLabel {{
    color: {C['muted']};
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.9px;
}}
QFrame#Card {{
    background: {C['bg2']};
    border: 1px solid {C['line']};
    border-radius: {R_BUYUK}px;
}}

/* ============ ust seritler ============ */
QFrame#TopBar {{
    background: {C['bg1']};
    border-bottom: 1px solid {C['line']};
}}
QFrame#BottomBar {{
    background: {C['bg1']};
    border-top: 1px solid {C['line2']};
}}
QLabel#TopTitle {{ font-size: 13px; font-weight: 700; }}
QLabel#TopPath {{ color: {C['muted']}; font-size: 11.5px; }}

/* ============ butonlar ============ */
QPushButton {{
    background: {C['bg2']};
    border: 1px solid {C['line2']};
    border-radius: {R_ORTA}px;
    padding: 6px 12px;
    color: {C['text2']};
    font-size: 12.5px;
    font-weight: 600;
    min-height: 18px;
}}
QPushButton:hover {{
    background: {C['bg3']};
    border-color: {C['line3']};
    color: {C['text']};
}}
QPushButton:pressed {{ background: {C['bg4']}; }}
QPushButton:disabled {{
    background: {C['bg1']};
    border-color: {C['line']};
    color: {C['muted']};
}}

QPushButton[kind="primary"] {{
    background: {GRADYAN};
    border-color: {C['accent_lo']};
    color: #06140A;
}}
QPushButton[kind="primary"]:hover {{
    background: {GRADYAN_HOVER}; border-color: {C['accent_hi']};
}}
QPushButton[kind="primary"]:disabled {{
    background: {C['accent_dim']}; border-color: {C['accent_dim']}; color: {C['muted']};
}}

/* ikincil dugme: zemini yok ama kenari var, tiklanabilir oldugu belli olsun */
QPushButton[kind="ghost"] {{
    background: transparent;
    border: 1px solid {C['line2']};
    color: {C['text2']};
}}
QPushButton[kind="ghost"]:hover {{
    background: {C['bg3']}; border-color: {C['line3']}; color: {C['text']};
}}

QPushButton[kind="danger"] {{ color: {C['red']}; border-color: {C['line2']}; }}
QPushButton[kind="danger"]:hover {{
    background: {C['red_dim']}; border-color: {C['red']}; color: #FFB3AE;
}}

/* dar seritlere sigan kucuk dugme: normal dolgu 32px'e ulasip seridi tasiriyor */
QPushButton[size="compact"] {{
    padding: 2px 9px;
    min-height: 14px;
    max-height: 22px;
    font-size: 11.5px;
}}

QToolButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {R_KUCUK}px;
    padding: 3px;
}}
QToolButton#IconButton:hover {{ background: {C['bg3']}; border-color: {C['line2']}; }}
QToolButton#IconButton:pressed {{ background: {C['bg4']}; }}

/* ============ girisler ============ */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {C['bg2']};
    border: 1px solid {C['line2']};
    border-radius: {R_ORTA}px;
    padding: 6px 9px;
    color: {C['text']};
    selection-background-color: {C['accent']};
    selection-color: #06140A;
}}
QLineEdit:hover, QSpinBox:hover {{ border-color: {C['line3']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    border-color: {C['accent']};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 15px; border: none; background: transparent;
    subcontrol-origin: border;
}}
QSpinBox::up-button {{ subcontrol-position: top right; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; }}
QSpinBox::up-arrow {{
    image: none; width: 0px; height: 0px; background: transparent;
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-bottom: 4px solid {C['muted']};
}}
QSpinBox::down-arrow {{
    image: none; width: 0px; height: 0px; background: transparent;
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-top: 4px solid {C['muted']};
}}
QSpinBox::up-arrow:hover {{ border-bottom-color: {C['accent']}; }}
QSpinBox::down-arrow:hover {{ border-top-color: {C['accent']}; }}

QPlainTextEdit#Composer {{
    background: {C['bg2']};
    border: 1px solid {C['line2']};
    border-radius: {R_BUYUK}px;
    padding: 9px 11px;
    font-size: 13px;
}}
QPlainTextEdit#Composer:focus {{ border-color: {C['accent']}; }}

QPlainTextEdit#CodeEdit {{
    background: {C['kod']};
    border: none;
    border-radius: 0px;
    padding: 6px 0px;
    font-family: {CODE_FONT};
    font-size: 12.5px;
}}
QPlainTextEdit#PromptEdit {{
    background: {C['kod']};
    border: 1px solid {C['line2']};
    border-radius: {R_ORTA}px;
    padding: 8px 10px;
    font-family: {CODE_FONT};
    font-size: 12.5px;
}}
QPlainTextEdit#PromptEdit:focus {{ border-color: {C['accent']}; }}

/* ============ combobox ============ */
QComboBox {{
    background: {C['bg2']};
    border: 1px solid {C['line2']};
    border-radius: {R_ORTA}px;
    padding: 5px 9px;
    color: {C['text']};
    min-height: 18px;
}}
QComboBox:hover {{ border-color: {C['line3']}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C['muted']};
    margin-right: 7px;
}}
QComboBox QAbstractItemView {{
    background: {C['bg2']};
    border: 1px solid {C['line2']};
    border-radius: {R_ORTA}px;
    padding: 3px;
    outline: none;
    selection-background-color: {C['bg4']};
    selection-color: {C['text']};
}}

/* ============ onay kutusu ============ */
QCheckBox {{ spacing: 8px; color: {C['text2']}; font-size: 12.5px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {C['line2']};
    border-radius: 4px;
    background: {C['bg2']};
}}
QCheckBox::indicator:hover {{ border-color: {C['accent']}; }}
QCheckBox::indicator:checked {{ background: {C['accent']}; border-color: {C['accent']}; }}

/* ============ kaydirici ============ */
QSlider::groove:horizontal {{ height: 3px; background: {C['line2']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {C['text']}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{ background: {C['accent_hi']}; }}

/* ============ agac ve liste ============ */
QTreeWidget, QListWidget, QTreeView, QListView {{
    background: {C['bg1']};
    border: none;
    outline: none;
    font-size: 12.5px;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 4px 3px;
    border-radius: {R_KUCUK}px;
    color: {C['text2']};
}}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {C['bg3']}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {C['bg4']}; color: {C['text']};
}}
QTreeWidget::branch {{ background: transparent; }}
QHeaderView::section {{ background: {C['bg1']}; border: none; color: {C['muted']}; padding: 3px; }}

/* ============ kaydirma cubugu ============ */
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['line2']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C['line3']}; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {C['line2']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {C['line3']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ border: none; background: {C['bg0']}; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QWidget#ChatBody {{ background: {C['bg0']}; }}
QWidget#PanelBody {{ background: {C['bg1']}; }}

/* ============ sohbet ============ */
QFrame#UserBubble {{
    background: {C['accent_dim']};
    border: 1px solid {C['accent_soft']};
    border-left: 2px solid {C['accent']};
    border-radius: {R_BUYUK}px;
}}
QFrame#AssistantBubble {{ background: transparent; border: none; }}
QFrame#SystemBubble {{
    background: {C['bg1']};
    border: 1px solid {C['line']};
    border-radius: {R_ORTA}px;
}}
QTextBrowser#Message {{ background: transparent; border: none; font-size: 13px; }}
QLabel#RoleName {{ font-weight: 700; font-size: 11.5px; letter-spacing: 0.4px; }}
QLabel#TimeStamp {{ color: {C['muted']}; font-size: 10.5px; }}
QLabel#EmptyState {{ color: {C['muted']}; font-size: 12.5px; }}

/* ============ arac kartlari ============ */
QFrame#ToolCard {{
    background: {C['bg2']};
    border: 1px solid {C['line']};
    border-left: 2px solid {C['line3']};
    border-radius: {R_ORTA}px;
}}
QFrame#ToolCard[state="running"] {{ border-left-color: {C['amber']}; }}
QFrame#ToolCard[state="ok"] {{ border-left-color: {C['green']}; }}
QFrame#ToolCard[state="fail"] {{ border-left-color: {C['red']}; }}
QFrame#ToolCard[state="denied"] {{ border-left-color: {C['muted']}; }}
QLabel#ToolTitle {{ font-weight: 600; font-size: 12px; color: {C['text']}; }}
QLabel#ToolTarget {{ color: {C['muted']}; font-family: {CODE_FONT}; font-size: 11.5px; }}
QTextBrowser#ToolOutput {{
    background: {C['kod']};
    border: 1px solid {C['line']};
    border-radius: {R_KUCUK}px;
    font-family: {CODE_FONT};
    font-size: 11.5px;
    color: {C['text2']};
}}

/* ============ rozetler ============ */
QLabel#Badge {{
    border-radius: {R_KUCUK}px;
    padding: 2px 7px;
    font-size: 10.5px;
    font-weight: 700;
    background: {C['bg3']};
    color: {C['muted']};
}}
QLabel#Badge[tone="accent"] {{ background: {C['accent_dim']}; color: {C['accent_hi']}; }}
QLabel#Badge[tone="green"] {{ background: {C['green_dim']}; color: {C['green']}; }}
QLabel#Badge[tone="red"] {{ background: {C['red_dim']}; color: #FFA9A3; }}
QLabel#Badge[tone="amber"] {{ background: {C['amber_dim']}; color: {C['amber']}; }}
QLabel#Badge[tone="violet"] {{ background: {C['violet_dim']}; color: {C['violet']}; }}

/* ============ durum serit ============ */
QFrame#StatusBar {{ background: {C['bg1']}; border-top: 1px solid {C['line']}; }}
QLabel#StatusText {{ color: {C['muted']}; font-size: 11px; }}
QLabel#StatusStrong {{ color: {C['text2']}; font-size: 11px; font-weight: 600; }}

/* ============ ayirici ============ */
QSplitter::handle {{ background: {C['line']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QSplitter::handle:hover {{ background: {C['accent']}; }}

/* ============ sekmeler ============ */
QTabWidget::pane {{ border: none; background: {C['kod']}; }}
QTabBar {{ background: {C['bg1']}; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: {C['bg1']};
    color: {C['muted']};
    border: none;
    border-right: 1px solid {C['line']};
    border-top: 2px solid transparent;
    padding: 6px 14px;
    font-size: 12px;
    min-width: 60px;
}}
QTabBar::tab:selected {{
    background: {C['kod']};
    color: {C['text']};
    border-top: 2px solid {C['accent']};
}}
QTabBar::tab:hover:!selected {{ background: {C['bg3']}; color: {C['text2']}; }}
QTabBar::close-button {{ image: none; subcontrol-position: right; }}

/* ============ diyalog ============ */
QMessageBox {{ background: {C['bg1']}; }}
QMessageBox QLabel {{ color: {C['text']}; }}
"""
