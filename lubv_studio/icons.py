"""Vektor ikonlar.

Emoji kullanmiyoruz: yazi tipine gore boyu degisiyor, hizasi kayiyor ve bazi
sistemlerde bos kare cikiyor. Butun ikonlar burada QPainter ile ciziliyor,
her ekranda ayni kalinlikta ve keskin gorunuyor.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

OLCEK = 3          # once buyuk ciz, sonra kucult: kenarlar puruzsuz olur
KALINLIK = 1.7


def _kalem_ayarla(boyaci: QPainter, renk: str, kalinlik: float = KALINLIK) -> None:
    kalem = QPen(QColor(renk))
    kalem.setWidthF(kalinlik)
    kalem.setCapStyle(Qt.PenCapStyle.RoundCap)
    kalem.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    boyaci.setPen(kalem)
    boyaci.setBrush(Qt.BrushStyle.NoBrush)


def _tuval(boyut: int) -> tuple[QPixmap, QPainter]:
    pix = QPixmap(boyut * OLCEK, boyut * OLCEK)
    pix.fill(Qt.GlobalColor.transparent)
    boyaci = QPainter(pix)
    boyaci.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    boyaci.scale(boyut * OLCEK / 24.0, boyut * OLCEK / 24.0)  # 24x24 tasarim izgarasi
    return pix, boyaci


def _bitir(pix: QPixmap, boyaci: QPainter, boyut: int) -> QIcon:
    boyaci.end()
    return QIcon(
        pix.scaled(
            boyut, boyut,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


# --------------------------------------------------------------------------
# Cizimler (hepsi 24x24 izgarada)
# --------------------------------------------------------------------------

def _dosyalar(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yol = QPainterPath()
    yol.moveTo(3.5, 6.5)
    yol.lineTo(9.5, 6.5)
    yol.lineTo(11.2, 8.8)
    yol.lineTo(20.5, 8.8)
    yol.lineTo(20.5, 18.5)
    yol.lineTo(3.5, 18.5)
    yol.closeSubpath()
    b.drawPath(yol)


def _git(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawLine(QPointF(7.5, 8.5), QPointF(7.5, 15.5))
    b.drawEllipse(QPointF(7.5, 6.0), 2.3, 2.3)
    b.drawEllipse(QPointF(7.5, 18.0), 2.3, 2.3)
    b.drawEllipse(QPointF(16.5, 6.0), 2.3, 2.3)
    yol = QPainterPath()
    yol.moveTo(16.5, 8.4)
    yol.lineTo(16.5, 10.5)
    yol.cubicTo(16.5, 13.6, 13.8, 13.2, 10.2, 14.4)
    b.drawPath(yol)


def _bellek(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawRoundedRect(QRectF(7.0, 7.0, 10.0, 10.0), 2.2, 2.2)
    b.drawRect(QRectF(10.2, 10.2, 3.6, 3.6))
    for k in (10.0, 13.5):
        b.drawLine(QPointF(k, 4.2), QPointF(k, 7.0))
        b.drawLine(QPointF(k, 17.0), QPointF(k, 19.8))
        b.drawLine(QPointF(4.2, k), QPointF(7.0, k))
        b.drawLine(QPointF(17.0, k), QPointF(19.8, k))


def _beyin(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    buyuk = QPainterPath()
    buyuk.moveTo(11.0, 3.6)
    buyuk.cubicTo(12.0, 8.6, 13.4, 10.0, 18.4, 11.0)
    buyuk.cubicTo(13.4, 12.0, 12.0, 13.4, 11.0, 18.4)
    buyuk.cubicTo(10.0, 13.4, 8.6, 12.0, 3.6, 11.0)
    buyuk.cubicTo(8.6, 10.0, 10.0, 8.6, 11.0, 3.6)
    b.drawPath(buyuk)
    kucuk = QPainterPath()
    kucuk.moveTo(18.0, 15.0)
    kucuk.cubicTo(18.4, 17.1, 18.9, 17.6, 21.0, 18.0)
    kucuk.cubicTo(18.9, 18.4, 18.4, 18.9, 18.0, 21.0)
    kucuk.cubicTo(17.6, 18.9, 17.1, 18.4, 15.0, 18.0)
    kucuk.cubicTo(17.1, 17.6, 17.6, 17.1, 18.0, 15.0)
    b.drawPath(kucuk)


def _geri(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yay = QPainterPath()
    yay.moveTo(5.0, 11.0)
    yay.arcTo(QRectF(5.0, 6.0, 14.0, 12.0), 180.0, -260.0)
    b.drawPath(yay)
    ok = QPainterPath()
    ok.moveTo(5.0, 6.2)
    ok.lineTo(5.0, 11.4)
    ok.lineTo(10.2, 11.4)
    b.drawPath(ok)


def _ayarlar(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawEllipse(QPointF(12.0, 12.0), 3.1, 3.1)
    b.save()
    b.translate(12.0, 12.0)
    for _ in range(8):
        b.drawLine(QPointF(0.0, -6.0), QPointF(0.0, -8.2))
        b.rotate(45.0)
    b.restore()
    b.drawEllipse(QPointF(12.0, 12.0), 7.1, 7.1)


def _yenile(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yay = QPainterPath()
    yay.moveTo(19.0, 12.0)
    yay.arcTo(QRectF(5.0, 5.0, 14.0, 14.0), 0.0, 290.0)
    b.drawPath(yay)
    ok = QPainterPath()
    ok.moveTo(15.4, 5.2)
    ok.lineTo(19.4, 5.2)
    ok.lineTo(19.4, 9.2)
    b.drawPath(ok)


def _klasor_ac(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yol = QPainterPath()
    yol.moveTo(3.5, 18.5)
    yol.lineTo(3.5, 6.5)
    yol.lineTo(9.3, 6.5)
    yol.lineTo(11.0, 8.8)
    yol.lineTo(17.5, 8.8)
    yol.lineTo(17.5, 11.0)
    b.drawPath(yol)
    alt = QPainterPath()
    alt.moveTo(3.5, 18.5)
    alt.lineTo(6.6, 11.4)
    alt.lineTo(21.0, 11.4)
    alt.lineTo(17.9, 18.5)
    alt.closeSubpath()
    b.drawPath(alt)


def _arti(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk, KALINLIK + 0.2)
    b.drawLine(QPointF(12.0, 6.0), QPointF(12.0, 18.0))
    b.drawLine(QPointF(6.0, 12.0), QPointF(18.0, 12.0))


def _gonder(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yol = QPainterPath()
    yol.moveTo(4.2, 12.0)
    yol.lineTo(19.6, 5.0)
    yol.lineTo(13.6, 19.4)
    yol.lineTo(11.6, 13.2)
    yol.closeSubpath()
    b.drawPath(yol)
    b.drawLine(QPointF(11.6, 13.2), QPointF(19.6, 5.0))


def _dur(b: QPainter, renk: str) -> None:
    b.setPen(Qt.PenStyle.NoPen)
    b.setBrush(QColor(renk))
    b.drawRoundedRect(QRectF(7.5, 7.5, 9.0, 9.0), 1.6, 1.6)


def _ara(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawEllipse(QPointF(10.8, 10.8), 5.3, 5.3)
    b.drawLine(QPointF(14.8, 14.8), QPointF(19.2, 19.2))


def _capraz(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawLine(QPointF(7.5, 7.5), QPointF(16.5, 16.5))
    b.drawLine(QPointF(16.5, 7.5), QPointF(7.5, 16.5))


def _ataç(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    yol = QPainterPath()
    yol.moveTo(16.4, 8.0)
    yol.lineTo(9.6, 14.8)
    yol.cubicTo(8.2, 16.2, 10.2, 18.2, 11.6, 16.8)
    yol.lineTo(18.0, 10.4)
    yol.cubicTo(20.4, 8.0, 16.8, 4.4, 14.4, 6.8)
    yol.lineTo(7.2, 14.0)
    yol.cubicTo(3.8, 17.4, 8.8, 22.4, 12.2, 19.0)
    b.drawPath(yol)


def _terminal(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawRoundedRect(QRectF(3.5, 5.0, 17.0, 14.0), 2.4, 2.4)
    ok = QPainterPath()
    ok.moveTo(7.4, 9.6)
    ok.lineTo(10.6, 12.2)
    ok.lineTo(7.4, 14.8)
    b.drawPath(ok)
    b.drawLine(QPointF(12.6, 15.0), QPointF(16.8, 15.0))


def _duzenle(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    govde = QPainterPath()
    govde.moveTo(5.0, 19.0)
    govde.lineTo(5.6, 15.2)
    govde.lineTo(15.8, 5.0)
    govde.lineTo(19.0, 8.2)
    govde.lineTo(8.8, 18.4)
    govde.closeSubpath()
    b.drawPath(govde)
    b.drawLine(QPointF(13.6, 7.2), QPointF(16.8, 10.4))


def _sil(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawLine(QPointF(4.6, 7.0), QPointF(19.4, 7.0))
    govde = QPainterPath()
    govde.moveTo(6.6, 7.0)
    govde.lineTo(7.5, 19.4)
    govde.lineTo(16.5, 19.4)
    govde.lineTo(17.4, 7.0)
    b.drawPath(govde)
    kapak = QPainterPath()
    kapak.moveTo(9.4, 7.0)
    kapak.lineTo(9.4, 4.8)
    kapak.lineTo(14.6, 4.8)
    kapak.lineTo(14.6, 7.0)
    b.drawPath(kapak)


def _kure(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    b.drawEllipse(QPointF(12.0, 12.0), 8.0, 8.0)
    b.drawLine(QPointF(4.0, 12.0), QPointF(20.0, 12.0))
    b.drawEllipse(QPointF(12.0, 12.0), 3.6, 8.0)


def _baglanti(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    sol = QPainterPath()
    sol.moveTo(11.0, 8.0)
    sol.lineTo(8.4, 8.0)
    sol.cubicTo(3.2, 8.0, 3.2, 16.0, 8.4, 16.0)
    sol.lineTo(11.0, 16.0)
    b.drawPath(sol)
    sag = QPainterPath()
    sag.moveTo(13.0, 8.0)
    sag.lineTo(15.6, 8.0)
    sag.cubicTo(20.8, 8.0, 20.8, 16.0, 15.6, 16.0)
    sag.lineTo(13.0, 16.0)
    b.drawPath(sag)
    b.drawLine(QPointF(8.6, 12.0), QPointF(15.4, 12.0))


def _liste(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk)
    for y in (7.5, 12.0, 16.5):
        b.drawLine(QPointF(9.0, y), QPointF(19.0, y))
        b.drawEllipse(QPointF(5.6, y), 1.1, 1.1)


def _chevron(b: QPainter, renk: str) -> None:
    _kalem_ayarla(b, renk, KALINLIK + 0.1)
    yol = QPainterPath()
    yol.moveTo(9.0, 8.0)
    yol.lineTo(14.4, 12.0)
    yol.lineTo(9.0, 16.0)
    b.drawPath(yol)


CIZIMLER = {
    "dosyalar": _dosyalar,
    "git": _git,
    "bellek": _bellek,
    "beyin": _beyin,
    "geri": _geri,
    "ayarlar": _ayarlar,
    "yenile": _yenile,
    "klasor": _klasor_ac,
    "arti": _arti,
    "gonder": _gonder,
    "dur": _dur,
    "ara": _ara,
    "capraz": _capraz,
    "atac": _ataç,
    "terminal": _terminal,
    "duzenle": _duzenle,
    "sil": _sil,
    "kure": _kure,
    "baglanti": _baglanti,
    "liste": _liste,
    "chevron": _chevron,
}

_ONBELLEK: dict[tuple[str, str, int], QIcon] = {}


def ikon(ad: str, renk: str, boyut: int = 20) -> QIcon:
    """Adi verilen ikonu istenen renkte uretir (sonuc onbellege alinir)."""
    anahtar = (ad, renk, boyut)
    if anahtar in _ONBELLEK:
        return _ONBELLEK[anahtar]
    cizim = CIZIMLER.get(ad)
    if cizim is None:
        return QIcon()
    pix, boyaci = _tuval(boyut)
    cizim(boyaci, renk)
    sonuc = _bitir(pix, boyaci, boyut)
    _ONBELLEK[anahtar] = sonuc
    return sonuc


def uygulama_ikonu(boyut: int = 256) -> QPixmap:
    """Pencere/gorev cubugu ikonu."""
    from PySide6.QtGui import QBrush, QFont, QLinearGradient

    pix = QPixmap(boyut, boyut)
    pix.fill(Qt.GlobalColor.transparent)
    b = QPainter(pix)
    b.setRenderHint(QPainter.RenderHint.Antialiasing)
    gecis = QLinearGradient(0, 0, boyut, boyut)
    gecis.setColorAt(0.0, QColor("#53FC18"))
    gecis.setColorAt(1.0, QColor("#00E701"))
    b.setBrush(QBrush(gecis))
    b.setPen(Qt.PenStyle.NoPen)
    kenar = boyut * 0.07
    b.drawRoundedRect(
        QRectF(kenar, kenar, boyut - 2 * kenar, boyut - 2 * kenar),
        boyut * 0.22, boyut * 0.22,
    )
    yazi = QFont("Segoe UI")
    yazi.setBold(True)
    yazi.setPixelSize(int(boyut * 0.54))
    b.setFont(yazi)
    b.setPen(QColor("#06140A"))
    b.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "L")
    b.end()
    return pix
