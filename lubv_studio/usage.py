"""Token ve maliyet takibi.

DeepSeek her istegin sonunda usage bilgisi doner. Burada onu dolar cinsine
cevirip hem oturum hem de gunluk/toplam bazda kalici olarak saklariz.

Fiyatlar 1M token basina USD (DeepSeek resmi fiyat sayfasi, Agustos 2026).
DeepSeek fiyatlari degistirirse Ayarlar > Maliyet bolumunden guncellenebilir.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import APP_DIR

USAGE_PATH = APP_DIR / "usage.json"

# model -> (cache hit girdi, cache miss girdi, cikti)   [USD / 1M token]
PRICING: dict[str, tuple[float, float, float]] = {
    "deepseek-v4-flash": (0.0028, 0.14, 0.28),
    "deepseek-v4-pro": (0.003625, 0.435, 0.87),
    # eski aliaslar hala calisirsa diye
    "deepseek-chat": (0.07, 0.56, 1.68),
    "deepseek-reasoner": (0.14, 0.55, 2.19),
}
VARSAYILAN_FIYAT = (0.0028, 0.14, 0.28)


def fiyat(model: str) -> tuple[float, float, float]:
    if model in PRICING:
        return PRICING[model]
    for anahtar, deger in PRICING.items():
        if anahtar in model:
            return deger
    return VARSAYILAN_FIYAT


@dataclass
class Kullanim:
    """Tek bir API cagrisinin sonucu."""
    model: str = ""
    girdi: int = 0
    cikti: int = 0
    cache_hit: int = 0
    cache_miss: int = 0
    dusunce: int = 0
    maliyet: float = 0.0
    zaman: float = field(default_factory=time.time)

    @classmethod
    def from_api(cls, model: str, ham: dict) -> "Kullanim":
        girdi = int(ham.get("prompt_tokens") or 0)
        cikti = int(ham.get("completion_tokens") or 0)
        hit = int(ham.get("prompt_cache_hit_tokens") or 0)
        miss = int(ham.get("prompt_cache_miss_tokens") or 0)
        if hit == 0 and miss == 0:
            detay = ham.get("prompt_tokens_details") or {}
            hit = int(detay.get("cached_tokens") or 0)
            miss = max(girdi - hit, 0)
        detay_c = ham.get("completion_tokens_details") or {}
        dusunce = int(detay_c.get("reasoning_tokens") or 0)

        p_hit, p_miss, p_out = fiyat(model)
        maliyet = (
            hit / 1_000_000 * p_hit
            + miss / 1_000_000 * p_miss
            + cikti / 1_000_000 * p_out
        )
        return cls(
            model=model, girdi=girdi, cikti=cikti, cache_hit=hit,
            cache_miss=miss, dusunce=dusunce, maliyet=maliyet,
        )


def para(tutar: float) -> str:
    """Kucuk tutarlari cent, buyukleri dolar olarak yazar."""
    if tutar <= 0:
        return "0.00¢"
    if tutar < 0.01:
        return f"{tutar * 100:.3f}¢"
    if tutar < 1:
        return f"{tutar * 100:.2f}¢"
    return f"${tutar:.4f}".rstrip("0").rstrip(".") if tutar < 10 else f"${tutar:.2f}"


def token_kisa(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.2f}M"


class UsageStore:
    """Oturum + gunluk + toplam kullanim kaydi."""

    def __init__(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.oturum: list[Kullanim] = []
        self.gunler: dict[str, dict] = {}
        self.toplam = {"girdi": 0, "cikti": 0, "maliyet": 0.0, "istek": 0}
        self.load()

    # ---------- kalicilik ----------

    def load(self) -> None:
        if not USAGE_PATH.exists():
            return
        try:
            ham = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
            self.gunler = ham.get("gunler", {}) or {}
            kayit = ham.get("toplam") or {}
            self.toplam.update({k: kayit.get(k, self.toplam[k]) for k in self.toplam})
        except Exception:
            pass

    def save(self) -> None:
        try:
            USAGE_PATH.write_text(
                json.dumps(
                    {"gunler": self.gunler, "toplam": self.toplam},
                    ensure_ascii=False, indent=1,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ---------- kayit ----------

    def ekle(self, kullanim: Kullanim) -> None:
        self.oturum.append(kullanim)

        gun = time.strftime("%Y-%m-%d", time.localtime(kullanim.zaman))
        kayit = self.gunler.setdefault(
            gun, {"girdi": 0, "cikti": 0, "maliyet": 0.0, "istek": 0}
        )
        kayit["girdi"] += kullanim.girdi
        kayit["cikti"] += kullanim.cikti
        kayit["maliyet"] += kullanim.maliyet
        kayit["istek"] += 1

        self.toplam["girdi"] += kullanim.girdi
        self.toplam["cikti"] += kullanim.cikti
        self.toplam["maliyet"] += kullanim.maliyet
        self.toplam["istek"] += 1

        # son 90 gunu tut
        if len(self.gunler) > 90:
            for eski in sorted(self.gunler)[:-90]:
                self.gunler.pop(eski, None)
        self.save()

    # ---------- ozetler ----------

    @property
    def oturum_maliyet(self) -> float:
        return sum(k.maliyet for k in self.oturum)

    @property
    def oturum_token(self) -> int:
        return sum(k.girdi + k.cikti for k in self.oturum)

    def bugun(self) -> dict:
        gun = time.strftime("%Y-%m-%d")
        return self.gunler.get(gun, {"girdi": 0, "cikti": 0, "maliyet": 0.0, "istek": 0})

    def son_gunler(self, adet: int = 14) -> list[tuple[str, dict]]:
        return [(g, self.gunler[g]) for g in sorted(self.gunler, reverse=True)[:adet]]

    def sifirla_oturum(self) -> None:
        self.oturum = []
