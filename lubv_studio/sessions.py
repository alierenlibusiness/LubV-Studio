"""Sohbet oturumlari: kalici kayit, listeleme, yeniden yukleme, silme.

Her oturum ~/.lubv_studio/sessions/<id>.json icinde tek dosyadir. Dosyada iki
sey durur:

  * mesajlar : modele gonderilen ham gecmis (role/content)
  * olaylar  : ekranda ne gorundugunun kaydi (balon, arac karti, sistem notu)

Ikisini ayri tutmak sart: modelin gecmisi kirpilabilir ama kullanicinin gordugu
dokum eksiksiz kalmalidir. Oturum acildiginda ekran olaylardan yeniden cizilir.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import SESSION_DIR

INDEX_PATH = SESSION_DIR / "index.json"
MAX_OTURUM = 300
BASLIK_UZUNLUK = 64


def _simdi() -> float:
    return time.time()


def _yeni_kimlik() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def baslik_uret(metin: str) -> str:
    """Ilk kullanici mesajindan okunabilir bir baslik cikarir."""
    temiz = " ".join((metin or "").split())
    # baglam olarak eklenen dosya bloklarini basliga tasima
    if temiz.startswith("[KULLANICININ EKLEDIGI DOSYALAR]"):
        parcalar = temiz.split("---")
        temiz = parcalar[-1].strip() if len(parcalar) > 1 else temiz
    if not temiz:
        return ""
    return temiz[:BASLIK_UZUNLUK] + ("..." if len(temiz) > BASLIK_UZUNLUK else "")


@dataclass
class Session:
    id: str = field(default_factory=_yeni_kimlik)
    baslik: str = ""
    proje: str = ""
    kip: str = "code"
    mod: str = "onay"
    model: str = ""
    created: float = field(default_factory=_simdi)
    updated: float = field(default_factory=_simdi)
    maliyet: float = 0.0
    mesajlar: list = field(default_factory=list)
    olaylar: list = field(default_factory=list)

    # ---------- turetilmis bilgiler ----------

    @property
    def gorunen_baslik(self) -> str:
        return self.baslik or "(isimsiz oturum)"

    @property
    def mesaj_sayisi(self) -> int:
        return len([o for o in self.olaylar if o.get("tip") in ("user", "assistant")])

    @property
    def bos_mu(self) -> bool:
        return not self.olaylar

    def zaman_etiketi(self) -> str:
        an = time.localtime(self.updated)
        bugun = time.localtime()
        if (an.tm_year, an.tm_yday) == (bugun.tm_year, bugun.tm_yday):
            return time.strftime("%H:%M", an)
        if an.tm_year == bugun.tm_year:
            return time.strftime("%d.%m %H:%M", an)
        return time.strftime("%d.%m.%Y", an)

    # ---------- olay ekleme ----------

    def olay_ekle(self, tip: str, **veri) -> None:
        kayit = {"tip": tip, "zaman": _simdi()}
        kayit.update(veri)
        self.olaylar.append(kayit)
        self.updated = _simdi()
        if not self.baslik and tip == "user":
            self.baslik = baslik_uret(veri.get("metin", ""))

    def son_olay(self, tip: str) -> dict | None:
        for kayit in reversed(self.olaylar):
            if kayit.get("tip") == tip:
                return kayit
        return None


class SessionStore:
    """Oturum dosyalarini yoneten kucuk depo."""

    def __init__(self) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- yol ----------

    @staticmethod
    def _yol(oturum_id: str) -> Path:
        # kimlik disaridan gelmez ama yine de dosya adina sadece guvenli
        # karakterler girsin
        guvenli = "".join(c for c in oturum_id if c.isalnum() or c in "-_")
        return SESSION_DIR / f"{guvenli}.json"

    # ---------- yazma / okuma ----------

    def kaydet(self, oturum: Session) -> bool:
        if oturum.bos_mu:
            return False
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        yol = self._yol(oturum.id)
        gecici = yol.with_suffix(".tmp")
        try:
            gecici.write_text(
                json.dumps(asdict(oturum), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            gecici.replace(yol)
        except Exception:
            return False
        self._indekse_yaz(oturum)
        return True

    def yukle(self, oturum_id: str) -> Session | None:
        yol = self._yol(oturum_id)
        if not yol.exists():
            return None
        try:
            ham = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:
            return None
        return self._sozlukten(ham)

    @staticmethod
    def _sozlukten(ham: dict) -> Session | None:
        if not isinstance(ham, dict) or not ham.get("id"):
            return None
        oturum = Session(id=str(ham["id"]))
        for alan in (
            "baslik", "proje", "kip", "mod", "model", "created", "updated",
            "maliyet", "mesajlar", "olaylar",
        ):
            if alan in ham:
                setattr(oturum, alan, ham[alan])
        return oturum

    # ---------- listeleme ----------

    def hepsi(self) -> list[Session]:
        """En yeniden eskiye dogru butun oturumlar."""
        kayitlar: list[Session] = []
        try:
            dosyalar = sorted(
                SESSION_DIR.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            return []
        for dosya in dosyalar:
            if dosya.name == INDEX_PATH.name:
                continue
            try:
                oturum = self._sozlukten(json.loads(dosya.read_text(encoding="utf-8")))
            except Exception:
                continue
            if oturum is not None:
                kayitlar.append(oturum)
        kayitlar.sort(key=lambda o: o.updated, reverse=True)
        return kayitlar

    def ozetler(self) -> list[Session]:
        """Listeleme icin hafif kayitlar.

        Panel her istek bitiminde tazeleniyor; butun oturum dosyalarini her
        seferinde acmak yuzlerce sohbet birikince gozle gorulur gecikme
        yaratiyordu. Ozetler ayri bir indeks dosyasindan okunur, indeks yoksa
        veya bozuksa dosyalardan bir kez yeniden kurulur.
        """
        indeks = self._indeksi_oku()
        if indeks is None:
            indeks = self._indeksi_kur()
        kayitlar: list[Session] = []
        for ham in indeks:
            oturum = Session(
                id=str(ham.get("id", "")), baslik=ham.get("baslik", ""),
                proje=ham.get("proje", ""), kip=ham.get("kip", "code"),
                mod=ham.get("mod", "onay"), model=ham.get("model", ""),
                created=float(ham.get("created", 0.0)),
                updated=float(ham.get("updated", 0.0)),
                maliyet=float(ham.get("maliyet", 0.0)),
            )
            if not oturum.id:
                continue
            # gercek olaylari tasimadan sayaci dogru gostermek icin
            oturum.olaylar = [{"tip": "user"}] * int(ham.get("mesaj", 0))
            kayitlar.append(oturum)
        kayitlar.sort(key=lambda o: o.updated, reverse=True)
        return kayitlar

    # ---------- silme ----------

    def sil(self, oturum_id: str) -> bool:
        yol = self._yol(oturum_id)
        try:
            if yol.exists():
                yol.unlink()
                self._indeksten_cikar(oturum_id)
                return True
        except Exception:
            return False
        return False

    def hepsini_sil(self) -> int:
        adet = 0
        for dosya in SESSION_DIR.glob("*.json"):
            if dosya.name == INDEX_PATH.name:
                continue
            try:
                dosya.unlink()
                adet += 1
            except Exception:
                continue
        self._indeksi_yaz([])
        return adet

    def yeniden_adlandir(self, oturum_id: str, baslik: str) -> bool:
        oturum = self.yukle(oturum_id)
        if oturum is None:
            return False
        oturum.baslik = (baslik or "").strip()[:120]
        return self.kaydet(oturum)

    # ---------- indeks ----------

    @staticmethod
    def _ozet_satiri(oturum: Session) -> dict:
        return {
            "id": oturum.id, "baslik": oturum.baslik, "proje": oturum.proje,
            "kip": oturum.kip, "mod": oturum.mod, "model": oturum.model,
            "created": oturum.created, "updated": oturum.updated,
            "maliyet": oturum.maliyet, "mesaj": oturum.mesaj_sayisi,
        }

    def _indeksi_oku(self) -> list[dict] | None:
        if not INDEX_PATH.exists():
            return None
        try:
            ham = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
        return ham if isinstance(ham, list) else None

    def _indeksi_yaz(self, satirlar: list[dict]) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        gecici = INDEX_PATH.with_suffix(".tmp")
        try:
            gecici.write_text(
                json.dumps(satirlar, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            gecici.replace(INDEX_PATH)
        except Exception:
            pass

    def _indekse_yaz(self, oturum: Session) -> None:
        satirlar = self._indeksi_oku()
        if satirlar is None:
            self._indeksi_kur(oturum)   # indeks yok veya bozuk, bastan kur
            return
        satirlar = [s for s in satirlar if s.get("id") != oturum.id]
        satirlar.append(self._ozet_satiri(oturum))
        satirlar.sort(key=lambda s: s.get("updated", 0), reverse=True)
        self._budala(satirlar)
        self._indeksi_yaz(satirlar)

    def _indeksten_cikar(self, oturum_id: str) -> None:
        satirlar = self._indeksi_oku()
        if satirlar is None:
            return
        self._indeksi_yaz([s for s in satirlar if s.get("id") != oturum_id])

    def _indeksi_kur(self, ek: Session | None = None) -> list[dict]:
        """Indeks yoksa veya bozuksa dosyalari bir kez tarayip yeniden kurar."""
        satirlar = [self._ozet_satiri(o) for o in self.hepsi()]
        if ek is not None and not any(s["id"] == ek.id for s in satirlar):
            satirlar.append(self._ozet_satiri(ek))
        satirlar.sort(key=lambda s: s.get("updated", 0), reverse=True)
        self._budala(satirlar)
        self._indeksi_yaz(satirlar)
        return satirlar

    def _budala(self, satirlar: list[dict]) -> None:
        """En eski oturumlari siler; klasor sonsuza kadar buyumesin."""
        for eski in satirlar[MAX_OTURUM:]:
            try:
                self._yol(str(eski.get("id", ""))).unlink(missing_ok=True)
            except Exception:
                continue
        del satirlar[MAX_OTURUM:]
