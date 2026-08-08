"""Markdown -> Qt zengin metni, sozdizimi renklendirme ve diff gorunumu."""

from __future__ import annotations

import difflib
import html
import re

from .theme import C, CODE_FONT

# --------------------------------------------------------------------------
# Sozdizimi renklendirme (dile bagimsiz, genel amacli)
# --------------------------------------------------------------------------

KEYWORDS = {
    # python
    "def", "class", "return", "import", "from", "as", "if", "elif", "else", "for",
    "while", "try", "except", "finally", "with", "lambda", "yield", "pass", "raise",
    "global", "nonlocal", "assert", "del", "in", "is", "not", "and", "or", "async",
    "await", "match", "case",
    # c ailesi / js / java / kotlin
    "function", "const", "let", "var", "new", "this", "super", "extends", "implements",
    "public", "private", "protected", "static", "final", "void", "int", "float",
    "double", "boolean", "string", "char", "long", "short", "struct", "enum",
    "interface", "package", "throw", "throws", "catch", "switch", "case", "break",
    "continue", "do", "typeof", "instanceof", "export", "default", "fun", "val",
    "when", "object", "suspend", "override", "data", "sealed", "abstract",
    # kabuk / sql
    "echo", "select", "insert", "update", "delete", "where", "join", "group", "order",
}
LITERALS = {"True", "False", "None", "null", "true", "false", "undefined", "nil", "self", "cls"}

_TOKEN_RE = re.compile(
    r"""(?P<comment>\#[^\n]*|//[^\n]*|/\*.*?\*/|&lt;!--.*?--&gt;)
       |(?P<string>\"\"\".*?\"\"\"|'''.*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)
       |(?P<decorator>@[A-Za-z_][\w.]*)
       |(?P<number>\b\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?\b|\b0x[0-9a-fA-F]+\b)
       |(?P<word>[A-Za-z_][\w]*)
    """,
    re.VERBOSE | re.DOTALL,
)

_SYNTAX_COLORS = {
    "comment": "#4E5654",
    "string": "#D9C26A",
    "number": "#E08B54",
    "keyword": "#5FE83A",
    "literal": "#FF8A8A",
    "decorator": "#D9A03C",
    "call": "#8FD9C0",
}


def highlight(code: str, lang: str = "") -> str:
    """Kacisi yapilmis kodu renkli HTML'e cevirir."""
    kacisli = html.escape(code, quote=False)

    def boya(match: re.Match) -> str:
        tur = match.lastgroup
        metin = match.group()
        if tur == "comment":
            return _span(metin, _SYNTAX_COLORS["comment"], italik=True)
        if tur == "string":
            return _span(metin, _SYNTAX_COLORS["string"])
        if tur == "number":
            return _span(metin, _SYNTAX_COLORS["number"])
        if tur == "decorator":
            return _span(metin, _SYNTAX_COLORS["decorator"])
        if tur == "word":
            if metin in KEYWORDS:
                return _span(metin, _SYNTAX_COLORS["keyword"])
            if metin in LITERALS:
                return _span(metin, _SYNTAX_COLORS["literal"])
            son = match.end()
            if son < len(kacisli) and kacisli[son] == "(":
                return _span(metin, _SYNTAX_COLORS["call"])
        return metin

    return _TOKEN_RE.sub(boya, kacisli)


def _span(metin: str, renk: str, italik: bool = False) -> str:
    stil = f"color:{renk};"
    if italik:
        stil += "font-style:italic;"
    return f'<span style="{stil}">{metin}</span>'


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_ITALIC_RE = re.compile(r"(?<![\*\w])\*([^\*\n]+)\*(?!\*)")
_STRIKE_RE = re.compile(r"~~(.+?)~~")
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<![\"'>=])(https?://[^\s<>\)]+)")


def _inline(metin: str) -> str:
    kacisli = html.escape(metin, quote=False)

    saklanan: list[str] = []

    def sakla(match: re.Match) -> str:
        saklanan.append(match.group(1))
        return f"\x00{len(saklanan) - 1}\x00"

    kacisli = _INLINE_CODE_RE.sub(sakla, kacisli)
    kacisli = _LINK_RE.sub(
        rf'<a href="\2" style="color:{C["accent_hi"]}; text-decoration:none;">\1</a>', kacisli
    )
    kacisli = _BOLD_RE.sub(r"<b>\1</b>", kacisli)
    kacisli = _ITALIC_RE.sub(r"<i>\1</i>", kacisli)
    kacisli = _STRIKE_RE.sub(r"<s>\1</s>", kacisli)
    kacisli = _BARE_URL_RE.sub(
        rf'<a href="\1" style="color:{C["accent_hi"]}; text-decoration:none;">\1</a>', kacisli
    )

    def geri(match: re.Match) -> str:
        kod = saklanan[int(match.group(1))]
        return (
            f'<span style="background-color:{C["bg4"]}; color:#8CFF62; '
            f'font-family:{CODE_FONT}; font-size:12px;">&nbsp;{kod}&nbsp;</span>'
        )

    return re.sub(r"\x00(\d+)\x00", geri, kacisli)


def _code_block(kod: str, dil: str) -> str:
    govde = highlight(kod.rstrip("\n"), dil)
    govde = govde.replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")
    baslik = ""
    if dil:
        baslik = (
            f'<tr><td style="background-color:{C["bg2"]}; padding:4px 12px;">'
            f'<span style="color:{C["muted"]}; font-size:11px;">{html.escape(dil)}</span>'
            f"</td></tr>"
        )
    return (
        '<table width="100%" cellspacing="0" cellpadding="0" '
        f'style="background-color:{C["kod"]}; margin:8px 0px;">'
        f"{baslik}"
        f'<tr><td style="background-color:{C["kod"]}; padding:10px 12px;">'
        f'<span style="font-family:{CODE_FONT}; font-size:12.5px; color:#D3D8D5;">{govde}</span>'
        "</td></tr></table>"
    )


def markdown_to_html(metin: str) -> str:
    """Model cevabini QTextBrowser'in anlayacagi HTML'e cevirir."""
    if not metin:
        return ""

    satirlar = metin.replace("\r\n", "\n").split("\n")
    parcalar: list[str] = []
    i = 0
    liste_acik = False

    def liste_kapat() -> None:
        nonlocal liste_acik
        if liste_acik:
            parcalar.append("</ul>")
            liste_acik = False

    while i < len(satirlar):
        satir = satirlar[i]

        # kod blogu
        if satir.lstrip().startswith("```"):
            liste_kapat()
            dil = satir.lstrip()[3:].strip()
            i += 1
            govde: list[str] = []
            while i < len(satirlar) and not satirlar[i].lstrip().startswith("```"):
                govde.append(satirlar[i])
                i += 1
            i += 1
            parcalar.append(_code_block("\n".join(govde), dil))
            continue

        ciplak = satir.strip()

        if not ciplak:
            liste_kapat()
            i += 1
            continue

        # yatay cizgi
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", ciplak):
            liste_kapat()
            parcalar.append(
                f'<div style="border-top:1px solid {C["line2"]}; margin:10px 0px;"></div>'
            )
            i += 1
            continue

        # baslik
        basliK = re.match(r"^(#{1,6})\s+(.*)$", ciplak)
        if basliK:
            liste_kapat()
            seviye = len(basliK.group(1))
            boyut = {1: 18, 2: 16, 3: 15, 4: 14, 5: 13, 6: 13}[seviye]
            parcalar.append(
                f'<div style="font-size:{boyut}px; font-weight:700; '
                f'margin:10px 0px 4px 0px; color:{C["text"]};">{_inline(basliK.group(2))}</div>'
            )
            i += 1
            continue

        # alinti
        if ciplak.startswith(">"):
            liste_kapat()
            parcalar.append(
                f'<div style="border-left:3px solid {C["line2"]}; padding-left:10px; '
                f'color:{C["text2"]}; margin:6px 0px;">{_inline(ciplak[1:].strip())}</div>'
            )
            i += 1
            continue

        # liste
        madde = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", satir)
        if madde:
            if not liste_acik:
                parcalar.append(
                    '<ul style="margin:4px 0px 4px 6px; -qt-list-indent:1;">'
                )
                liste_acik = True
            parcalar.append(f"<li style='margin:2px 0px;'>{_inline(madde.group(2))}</li>")
            i += 1
            continue

        liste_kapat()
        parcalar.append(
            f'<div style="margin:4px 0px; line-height:154%;">{_inline(satir)}</div>'
        )
        i += 1

    liste_kapat()
    return (
        f'<div style="color:{C["text"]};">' + "".join(parcalar) + "</div>"
    )


# --------------------------------------------------------------------------
# Diff
# --------------------------------------------------------------------------

def diff_to_html(eski: str, yeni: str, baslik: str = "") -> str:
    eski_satir = eski.splitlines()
    yeni_satir = yeni.splitlines()
    fark = list(
        difflib.unified_diff(eski_satir, yeni_satir, lineterm="", n=3)
    )

    if not fark:
        return (
            f'<span style="color:{C["muted"]}; font-family:{CODE_FONT};">'
            "Icerik ayni, degisiklik yok.</span>"
        )

    satirlar: list[str] = []
    ekleme = silme = 0
    for satir in fark[2:]:  # ilk iki satir --- / +++
        kacisli = html.escape(satir, quote=False).replace(" ", "&nbsp;")
        if satir.startswith("+"):
            ekleme += 1
            renk, zemin = "#8CFF62", "#12240A"
        elif satir.startswith("-"):
            silme += 1
            renk, zemin = "#FF8A8A", "#2E1414"
        elif satir.startswith("@@"):
            renk, zemin = C["accent_hi"], C["bg3"]
        else:
            renk, zemin = C["text2"], "transparent"
        satirlar.append(
            f'<div style="background-color:{zemin}; color:{renk}; '
            f'font-family:{CODE_FONT}; font-size:12px; white-space:pre;">{kacisli or "&nbsp;"}</div>'
        )

    ozet = (
        f'<div style="color:{C["muted"]}; font-size:12px; margin-bottom:6px;">'
        f'{html.escape(baslik)} &nbsp; <span style="color:#7EE787;">+{ekleme}</span> '
        f'<span style="color:#FF9C95;">-{silme}</span></div>'
    )
    return ozet + "".join(satirlar)


def plain_to_html(metin: str, renk: str | None = None) -> str:
    renk = renk or C["text2"]
    kacisli = html.escape(metin or "", quote=False).replace("\n", "<br>").replace(" ", "&nbsp;")
    return (
        f'<span style="font-family:{CODE_FONT}; font-size:12px; color:{renk};">{kacisli}</span>'
    )
