"""Kod editoru: satir numarasi, sozdizimi renklendirme, sekmeler, kaydetme."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor,
    QTextFormat, QTextOption,
)
from PySide6.QtWidgets import (
    QFrame, QLabel, QPlainTextEdit, QTabBar, QTabWidget, QTextEdit,
    QToolButton, QVBoxLayout, QWidget,
)

from .i18n import t
from . import platform_
from .i18n import t
from .icons import ikon
from .theme import C

# --------------------------------------------------------------------------
# Dil tanimlari
# --------------------------------------------------------------------------

ORTAK = [
    "if", "else", "for", "while", "return", "break", "continue", "class",
    "new", "try", "catch", "finally", "throw", "switch", "case", "default",
    "import", "export", "from", "as", "in", "of", "do", "true", "false", "null",
]
DILLER = {
    "python": {
        "ext": {".py", ".pyw", ".pyi"},
        "kw": ORTAK + [
            "def", "lambda", "yield", "pass", "raise", "with", "assert", "del",
            "global", "nonlocal", "async", "await", "elif", "except", "not",
            "and", "or", "is", "None", "True", "False", "self", "cls", "match",
        ],
        "comment": "#",
    },
    "javascript": {
        "ext": {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"},
        "kw": ORTAK + [
            "function", "const", "let", "var", "this", "typeof", "instanceof",
            "async", "await", "extends", "implements", "interface", "type",
            "enum", "public", "private", "readonly", "static", "undefined",
        ],
        "comment": "//",
    },
    "java": {
        "ext": {".java", ".kt", ".kts", ".cs", ".c", ".h", ".cpp", ".hpp", ".go", ".rs", ".swift"},
        "kw": ORTAK + [
            "public", "private", "protected", "static", "final", "void", "int",
            "float", "double", "boolean", "char", "long", "short", "struct",
            "enum", "interface", "package", "extends", "implements", "abstract",
            "fun", "val", "var", "when", "object", "override", "suspend", "data",
            "func", "let", "mut", "impl", "trait", "pub", "namespace", "using",
        ],
        "comment": "//",
    },
    "web": {
        "ext": {".html", ".htm", ".xml", ".vue", ".svelte", ".css", ".scss", ".less"},
        "kw": [
            "html", "head", "body", "div", "span", "script", "style", "class",
            "id", "href", "src", "important", "media", "import", "keyframes",
        ],
        "comment": "",
    },
    "data": {
        "ext": {".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".properties", ".env"},
        "kw": ["true", "false", "null", "yes", "no", "on", "off"],
        "comment": "#",
    },
    "shell": {
        "ext": {".sh", ".bat", ".cmd", ".ps1"},
        "kw": [
            "echo", "cd", "set", "if", "else", "for", "do", "done", "then", "fi",
            "function", "param", "return", "exit", "call", "rem", "git", "python",
            "npm", "pip",
        ],
        "comment": "#",
    },
    "markdown": {"ext": {".md", ".markdown", ".txt", ".log"}, "kw": [], "comment": ""},
}

# Kod icinde neon yesil yorucu olur: vurgu rengi yumusatilmis tonu kullanilir,
# tam parlak yesil sadece arayuz ogelerine ayrilir.
# Her belirtec turu ayri renkte. Yesil dilin iskeletine ayrildi; okunurluk icin
# kalan turler farkli tonlarda, hepsi siyah zeminde en az 4.5:1 kontrastta.
RENKLER = {
    "keyword": "#5FE83A",    # def, class, if, return: dilin iskeleti
    "builtin": "#4FD6C8",    # print, len, range: dilin hazir araclari
    "self": "#FF7B72",       # self, this, cls: ozel isaretciler
    "literal": "#FF9B6A",    # True, False, None
    "string": "#E3C877",     # metinler
    "escape": "#F0A868",     # metin icindeki kacis dizileri
    "number": "#E08B54",
    "function": "#8FD9C0",   # cagrilar
    "class": "#EAF2ED",      # tanimlanan sinif ve fonksiyon adlari
    "decorator": "#D9A03C",
    "parametre": "#C3CBD6",  # normal tanimlayicilar
    "operator": "#8A93A0",   # + - = == -> gibi isaretler
    "punct": "#6E7A8C",      # parantez, virgul
    "comment": "#4E5654",
}

# Dile ozgu hazir isimler: kullanicinin yazdigi adlardan ayrilsin diye
BUILTINS = {
    "python": {
        "print", "len", "range", "str", "int", "float", "bool", "list", "dict",
        "set", "tuple", "open", "type", "isinstance", "enumerate", "zip", "map",
        "filter", "sorted", "sum", "min", "max", "abs", "round", "super",
        "property", "staticmethod", "classmethod", "Exception", "ValueError",
        "TypeError", "KeyError", "IndexError", "RuntimeError", "OSError",
    },
    "javascript": {
        "console", "document", "window", "JSON", "Math", "Array", "Object",
        "String", "Number", "Boolean", "Promise", "Map", "Set", "Date",
        "parseInt", "parseFloat", "fetch", "setTimeout", "setInterval",
    },
    "java": {
        "System", "String", "Integer", "Double", "Boolean", "List", "Map",
        "ArrayList", "HashMap", "Exception", "Math", "Optional", "Stream",
    },
    "shell": {"echo", "cd", "ls", "cat", "grep", "curl", "git", "python", "npm", "pip"},
}
OZEL_ISARETCILER = {"self", "this", "cls", "super", "base"}
SABITLER = {"True", "False", "None", "null", "true", "false", "undefined", "nil", "NULL"}


def dil_bul(yol: str | Path) -> str:
    uzanti = Path(yol).suffix.lower()
    for ad, bilgi in DILLER.items():
        if uzanti in bilgi["ext"]:
            return ad
    return "markdown"


class Highlighter(QSyntaxHighlighter):
    """Genel amacli, dile gore ayarlanan renklendirici."""

    def __init__(self, document, dil: str = "python") -> None:
        super().__init__(document)
        self.kurallar: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self.coklu_baslangic: QRegularExpression | None = None
        self.coklu_bitis: QRegularExpression | None = None
        self.coklu_format = self._format(RENKLER["string"])
        self.set_language(dil)

    @staticmethod
    def _format(renk: str, kalin: bool = False, italik: bool = False) -> QTextCharFormat:
        bicim = QTextCharFormat()
        bicim.setForeground(QColor(renk))
        if kalin:
            bicim.setFontWeight(QFont.Weight.Bold)
        if italik:
            bicim.setFontItalic(True)
        return bicim

    def set_language(self, dil: str) -> None:
        self.dil = dil
        bilgi = DILLER.get(dil, DILLER["markdown"])
        self.kurallar = []

        # Sira onemlidir: sonra eklenen kural onceki rengi ezer, bu yuzden
        # genel olandan ozele dogru gidilir.

        # 1) isaretler ve noktalama en altta
        self.kurallar.append((
            QRegularExpression(r"[+\-*/%=<>!&|^~]+"), self._format(RENKLER["operator"])
        ))
        self.kurallar.append((
            QRegularExpression(r"[\(\)\[\]\{\},;:]"), self._format(RENKLER["punct"])
        ))

        # 2) cagrilar
        self.kurallar.append((
            QRegularExpression(r"\b(\w+)(?=\s*\()"), self._format(RENKLER["function"])
        ))

        # 3) dilin hazir isimleri, kullanicinin yazdiklarindan ayrilsin
        hazir = BUILTINS.get(dil, set())
        if hazir:
            desen = r"\b(" + "|".join(sorted(hazir, key=len, reverse=True)) + r")\b"
            self.kurallar.append((
                QRegularExpression(desen), self._format(RENKLER["builtin"])
            ))

        # 4) sayilar
        self.kurallar.append((
            QRegularExpression(
                r"\b0[xXbBoO][0-9a-fA-F_]+\b|\b\d[\d_]*(\.\d+)?([eE][+-]?\d+)?\b"
            ),
            self._format(RENKLER["number"]),
        ))

        # 5) anahtar kelimeler
        if bilgi["kw"]:
            anahtarlar = sorted(set(bilgi["kw"]) - SABITLER, key=len, reverse=True)
            if anahtarlar:
                desen = r"\b(" + "|".join(anahtarlar) + r")\b"
                self.kurallar.append((
                    QRegularExpression(desen), self._format(RENKLER["keyword"])
                ))

        # 6) sabitler ve ozel isaretciler
        self.kurallar.append((
            QRegularExpression(r"\b(" + "|".join(sorted(SABITLER)) + r")\b"),
            self._format(RENKLER["literal"]),
        ))
        self.kurallar.append((
            QRegularExpression(r"\b(" + "|".join(sorted(OZEL_ISARETCILER)) + r")\b"),
            self._format(RENKLER["self"], italik=True),
        ))

        # 7) tanimlanan sinif ve fonksiyon adlari, dekoratorler
        self.kurallar.append((
            QRegularExpression(r"\b(?:class|def|function|fun|interface|struct)\s+(\w+)"),
            self._format(RENKLER["class"], kalin=True),
        ))
        self.kurallar.append((
            QRegularExpression(r"@[\w.]+"), self._format(RENKLER["decorator"])
        ))
        # metinler
        metin = self._format(RENKLER["string"])
        for desen in (r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'", r"`[^`]*`"):
            self.kurallar.append((QRegularExpression(desen), metin))
        # metin icindeki kacis dizileri metinden bir ton ayrilsin
        self.kurallar.append((
            QRegularExpression(r"\\[nrtvbf0'\"\\]|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}"),
            self._format(RENKLER["escape"]),
        ))

        # yorumlar
        yorum = self._format(RENKLER["comment"], italik=True)
        if dil == "python":
            self.kurallar.append((QRegularExpression(r"#[^\n]*"), yorum))
            self.coklu_baslangic = QRegularExpression(r'"""')
            self.coklu_bitis = QRegularExpression(r'"""')
        elif dil in ("javascript", "java"):
            self.kurallar.append((QRegularExpression(r"//[^\n]*"), yorum))
            self.coklu_baslangic = QRegularExpression(r"/\*")
            self.coklu_bitis = QRegularExpression(r"\*/")
        elif dil == "web":
            self.coklu_baslangic = QRegularExpression(r"<!--")
            self.coklu_bitis = QRegularExpression(r"-->")
            self.kurallar.append((
                QRegularExpression(r"</?[\w\-]+"), self._format(RENKLER["keyword"], kalin=True)
            ))
        elif dil in ("data", "shell"):
            self.kurallar.append((QRegularExpression(r"#[^\n]*"), yorum))
            self.coklu_baslangic = None
            self.coklu_bitis = None
        else:
            self.coklu_baslangic = None
            self.coklu_bitis = None

        if dil == "markdown":
            self.kurallar = [
                (QRegularExpression(r"^#{1,6}\s.*$"), self._format(RENKLER["class"], kalin=True)),
                (QRegularExpression(r"\*\*[^\*]+\*\*"), self._format(C["text"], kalin=True)),
                (QRegularExpression(r"`[^`]+`"), self._format(RENKLER["string"])),
                (QRegularExpression(r"^\s*[-*+]\s"), self._format(RENKLER["decorator"])),
            ]

        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        for desen, bicim in self.kurallar:
            it = desen.globalMatch(text)
            while it.hasNext():
                es = it.next()
                if es.lastCapturedIndex() >= 1 and es.capturedStart(1) >= 0:
                    self.setFormat(es.capturedStart(1), es.capturedLength(1), bicim)
                else:
                    self.setFormat(es.capturedStart(), es.capturedLength(), bicim)

        if not self.coklu_baslangic:
            return

        self.setCurrentBlockState(0)
        basla = 0
        if self.previousBlockState() != 1:
            es = self.coklu_baslangic.match(text)
            basla = es.capturedStart() if es.hasMatch() else -1

        while basla >= 0:
            bitis_es = self.coklu_bitis.match(text, basla + 1)
            if bitis_es.hasMatch():
                uzunluk = bitis_es.capturedEnd() - basla
                self.setCurrentBlockState(0)
            else:
                uzunluk = len(text) - basla
                self.setCurrentBlockState(1)
            self.setFormat(basla, uzunluk, self.coklu_format)
            sonraki = self.coklu_baslangic.match(text, basla + uzunluk)
            basla = sonraki.capturedStart() if sonraki.hasMatch() else -1


class _SatirNoAlani(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.satir_no_genisligi(), 0)

    def paintEvent(self, event):  # noqa: N802
        self.editor.satir_no_ciz(event)


class CodeEditor(QPlainTextEdit):
    """Satir numarali, renklendirilmis kod alani."""

    kaydet_istendi = Signal()

    def __init__(self, parent=None, font_size: int = 13) -> None:
        super().__init__(parent)
        self.setObjectName("CodeEdit")
        self.satir_alani = _SatirNoAlani(self)

        yazi = platform_.kod_yazi_tipi(font_size)
        self.setFont(yazi)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.blockCountChanged.connect(self._genislik_guncelle)
        self.updateRequest.connect(self._alan_guncelle)
        self.cursorPositionChanged.connect(self._satir_vurgula)
        self._genislik_guncelle()
        self._satir_vurgula()

    # -- satir numarasi --

    def satir_no_genisligi(self) -> int:
        basamak = max(2, len(str(max(1, self.blockCount()))))
        return 18 + self.fontMetrics().horizontalAdvance("9") * basamak

    def _genislik_guncelle(self) -> None:
        self.setViewportMargins(self.satir_no_genisligi(), 0, 0, 0)

    def _alan_guncelle(self, rect: QRect, dy: int) -> None:
        if dy:
            self.satir_alani.scroll(0, dy)
        else:
            self.satir_alani.update(0, rect.y(), self.satir_alani.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._genislik_guncelle()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.satir_alani.setGeometry(
            QRect(cr.left(), cr.top(), self.satir_no_genisligi(), cr.height())
        )

    def satir_no_ciz(self, event) -> None:
        boyaci = QPainter(self.satir_alani)
        boyaci.fillRect(event.rect(), QColor("#0E121A"))

        blok = self.firstVisibleBlock()
        numara = blok.blockNumber()
        ust = round(self.blockBoundingGeometry(blok).translated(self.contentOffset()).top())
        alt = ust + round(self.blockBoundingRect(blok).height())
        aktif = self.textCursor().blockNumber()

        while blok.isValid() and ust <= event.rect().bottom():
            if blok.isVisible() and alt >= event.rect().top():
                boyaci.setPen(QColor(C["accent_hi"] if numara == aktif else "#3B4759"))
                boyaci.drawText(
                    0, ust, self.satir_alani.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(numara + 1),
                )
            blok = blok.next()
            ust = alt
            alt = ust + round(self.blockBoundingRect(blok).height())
            numara += 1

    def _satir_vurgula(self) -> None:
        secimler = []
        if not self.isReadOnly():
            secim = QTextEdit.ExtraSelection()
            secim.format.setBackground(QColor("#151B26"))
            secim.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            secim.cursor = self.textCursor()
            secim.cursor.clearSelection()
            secimler.append(secim)
        self.setExtraSelections(secimler)

    # -- klavye --

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.kaydet_istendi.emit()
            return
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        super().keyPressEvent(event)


class EditorTabs(QTabWidget):
    """Acik dosyalar. VS Code'daki gibi sekmeli."""

    dosya_kaydedildi = Signal(str)
    durum_degisti = Signal()

    def __init__(self, parent=None, font_size: int = 13) -> None:
        super().__init__(parent)
        self.font_size = font_size
        self.setTabsClosable(False)   # kapatma dugmesini kendimiz koyuyoruz
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.sekme_kapat)
        self.currentChanged.connect(lambda _: self.durum_degisti.emit())
        self.acik: dict[str, CodeEditor] = {}   # mutlak yol -> editor

    # ---------- dosya islemleri ----------

    def dosya_ac(self, yol: str | Path, satir: int | None = None) -> bool:
        yol = str(Path(yol).resolve())
        p = Path(yol)
        if not p.is_file():
            return False
        try:
            if p.stat().st_size > 3_000_000:
                return False
            icerik = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return False

        if yol in self.acik:
            editor = self.acik[yol]
            self.setCurrentWidget(editor)
        else:
            editor = CodeEditor(font_size=self.font_size)
            editor.setPlainText(icerik)
            editor.document().setModified(False)
            editor.highlighter = Highlighter(editor.document(), dil_bul(yol))
            editor.dosya_yolu = yol
            editor.kaydet_istendi.connect(self.aktifi_kaydet)
            editor.document().modificationChanged.connect(
                lambda _=None, e=editor: self._basligi_tazele(e)
            )
            self.acik[yol] = editor
            self.addTab(editor, p.name)
            idx = self.indexOf(editor)
            self.setTabToolTip(idx, yol)
            self._kapat_dugmesi_ekle(idx)
            self.setCurrentWidget(editor)

        if satir:
            imlec = editor.textCursor()
            imlec.movePosition(QTextCursor.MoveOperation.Start)
            imlec.movePosition(
                QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, max(0, satir - 1)
            )
            editor.setTextCursor(imlec)
            editor.centerCursor()

        editor.setFocus()
        self.durum_degisti.emit()
        return True

    def _kapat_dugmesi_ekle(self, index: int) -> None:
        """Sekmenin sagina kendi cizdigimiz kapatma dugmesini koyar."""
        dugme = QToolButton()
        dugme.setObjectName("TabClose")
        dugme.setFixedSize(QSize(16, 16))
        dugme.setIconSize(QSize(10, 10))
        dugme.setIcon(ikon("capraz", C["muted"], 10))
        dugme.setCursor(Qt.CursorShape.PointingHandCursor)
        dugme.setToolTip(t("Sekmeyi kapat"))
        dugme.setAutoRaise(True)
        dugme.clicked.connect(lambda: self._dugmeden_kapat(dugme))
        self.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, dugme)

    def _dugmeden_kapat(self, dugme) -> None:
        """Sekme sirasi degisebildigi icin dugmeden indeksi anlik bulunur."""
        for i in range(self.count()):
            if self.tabBar().tabButton(i, QTabBar.ButtonPosition.RightSide) is dugme:
                self.sekme_kapat(i)
                return

    def _basligi_tazele(self, editor: CodeEditor) -> None:
        idx = self.indexOf(editor)
        if idx < 0:
            return
        ad = Path(editor.dosya_yolu).name
        self.setTabText(idx, f"● {ad}" if editor.document().isModified() else ad)
        self.durum_degisti.emit()

    def aktifi_kaydet(self) -> bool:
        editor = self.currentWidget()
        if not isinstance(editor, CodeEditor):
            return False
        return self.kaydet(editor)

    def kaydet(self, editor: CodeEditor) -> bool:
        try:
            Path(editor.dosya_yolu).write_text(
                editor.toPlainText(), encoding="utf-8", newline="\n"
            )
        except Exception:
            return False
        editor.document().setModified(False)
        self._basligi_tazele(editor)
        self.dosya_kaydedildi.emit(editor.dosya_yolu)
        return True

    def hepsini_kaydet(self) -> int:
        adet = 0
        for editor in list(self.acik.values()):
            if editor.document().isModified() and self.kaydet(editor):
                adet += 1
        return adet

    def sekme_kapat(self, index: int) -> None:
        widget = self.widget(index)
        if isinstance(widget, CodeEditor):
            self.acik.pop(widget.dosya_yolu, None)
        self.removeTab(index)
        self.durum_degisti.emit()

    def hepsini_kapat(self) -> None:
        while self.count():
            self.sekme_kapat(0)

    def diskten_tazele(self, yol: str) -> None:
        """Ajan dosyayi degistirdiginde acik sekmeyi gunceller."""
        yol = str(Path(yol).resolve())
        editor = self.acik.get(yol)
        if editor is None:
            return
        try:
            yeni = Path(yol).read_text(encoding="utf-8", errors="replace")
        except Exception:
            # dosya silinmis olabilir
            idx = self.indexOf(editor)
            if idx >= 0:
                self.sekme_kapat(idx)
            return
        if yeni == editor.toPlainText():
            return
        imlec_pos = editor.textCursor().position()
        kaydirma = editor.verticalScrollBar().value()
        editor.setPlainText(yeni)
        editor.document().setModified(False)
        imlec = editor.textCursor()
        imlec.setPosition(min(imlec_pos, len(yeni)))
        editor.setTextCursor(imlec)
        editor.verticalScrollBar().setValue(kaydirma)
        self._basligi_tazele(editor)

    # ---------- durum ----------

    @property
    def aktif_yol(self) -> str:
        editor = self.currentWidget()
        return editor.dosya_yolu if isinstance(editor, CodeEditor) else ""

    def kirli_var_mi(self) -> bool:
        return any(e.document().isModified() for e in self.acik.values())

    def acik_yollar(self) -> list[str]:
        return list(self.acik.keys())

    def imlec_konumu(self) -> tuple[int, int]:
        editor = self.currentWidget()
        if not isinstance(editor, CodeEditor):
            return (0, 0)
        imlec = editor.textCursor()
        return (imlec.blockNumber() + 1, imlec.columnNumber() + 1)


class WelcomeView(QFrame):
    """Hicbir dosya acik degilken gosterilen ekran."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        duzen = QVBoxLayout(self)
        duzen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        duzen.setSpacing(10)

        logo = QLabel("LUBV")
        logo.setStyleSheet(
            f"font-size:42px; font-weight:800; color:{C['accent']}; letter-spacing:6px;"
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        alt = QLabel(t("DeepSeek ile vibe coding stüdyosu"))
        alt.setStyleSheet(f"color:{C['muted']}; font-size:14px;")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ipuclari = QLabel(
            "Soldan bir dosya sec ve ac  ·  Sagdaki sohbetten LUBV'ye ne isteyecegini yaz\n"
            "Ctrl+S kaydeder  ·  Ctrl+` terminali acar  ·  Ctrl+B dosya panelini gizler"
        )
        ipuclari.setStyleSheet(f"color:{C['line2']}; font-size:12px;")
        ipuclari.setAlignment(Qt.AlignmentFlag.AlignCenter)

        duzen.addWidget(logo)
        duzen.addWidget(alt)
        duzen.addSpacing(14)
        duzen.addWidget(ipuclari)
