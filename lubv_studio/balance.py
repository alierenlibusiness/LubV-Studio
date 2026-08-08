"""Bakiye izleyici: kalan krediyi arka planda yenileyip ust serite yazar.

Ag istegi arayuz thread'inde yapilamaz, yoksa her yenilemede pencere donuyor.
Burada tek bir arka plan thread'i belirli araliklarla bakiyeyi ceker ve sinyalle
arayuze verir. Bir istek biter bitmez de zorla tazeleme istenebilir; boylece
harcama ekrana aninda yansir.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from .api import Bakiye, DeepSeekClient

EN_KISA_ARALIK = 10       # saniye: bundan daha sik sorulmaz
HATA_ARALIGI = 120        # hata alindiginda bu kadar bekle, sunucuyu yorma
# Kapanista bu thread'i beklemek gerekiyor; istek ne kadar uzun surerse
# uygulama o kadar gec kapanir. Bakiye sorgusu icin kisa bir sure yeterli.
ISTEK_ZAMAN_ASIMI = 8


class BalanceWatcher(QThread):
    """Belirli araliklarla bakiyeyi ceker, degisince sinyal verir."""

    guncellendi = Signal(object)   # Bakiye

    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self._dur = threading.Event()
        self._tetik = threading.Event()
        self._son: Bakiye | None = None

    # ---------- disaridan kontrol ----------

    def hemen_yenile(self) -> None:
        """Bir sonraki dongusunu beklemeden hemen sorsun."""
        self._tetik.set()

    def durdur(self) -> None:
        self._dur.set()
        self._tetik.set()

    @property
    def son_deger(self) -> Bakiye | None:
        return self._son

    # ---------- dongu ----------

    def _aralik(self, sonuc: Bakiye) -> float:
        if not sonuc.gecerli:
            return HATA_ARALIGI
        istenen = int(getattr(self.cfg, "balance_refresh", 45) or 45)
        return max(EN_KISA_ARALIK, istenen)

    def run(self) -> None:
        while not self._dur.is_set():
            sonuc = self._cek()
            if sonuc is not None:
                self._son = sonuc
                self.guncellendi.emit(sonuc)
                bekleme = self._aralik(sonuc)
            else:
                bekleme = HATA_ARALIGI

            # tetiklenirse erken uyanir, yoksa suresi dolunca
            self._tetik.wait(bekleme)
            self._tetik.clear()

    def _cek(self) -> Bakiye | None:
        if not getattr(self.cfg, "show_balance", True):
            return None
        anahtar = (self.cfg.api_key or "").strip()
        if not anahtar:
            return Bakiye(mesaj="API anahtari girilmemis.")
        try:
            return DeepSeekClient(anahtar, self.cfg.base_url).bakiye(
                zaman_asimi=ISTEK_ZAMAN_ASIMI
            )
        except Exception as exc:   # ag katmani beklenmedik bir sey atarsa
            return Bakiye(mesaj=str(exc))
