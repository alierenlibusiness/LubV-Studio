"""DeepSeek API istemcisi - streaming sohbet, baglanti testi, bakiye/hata mesajlari."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Iterator

import requests

from .i18n import t


class ApiError(Exception):
    """Kullaniciya gosterilebilir, arayuz diline cevrilmis API hatasi.

    `gecici` alani "beklersem duzelir mi" sorusunu cevaplar. Ajan dongusu bu
    alana bakarak yeniden deneyip denemeyecegine karar verir; mesaj metnine
    bakmak ceviri acilinca bozulan bir yontemdi.

    Varsayilan None, yani "bilinmiyor": cagiran bilerek isaretlemediyse karar
    metin sezgilerine birakilir. False verilseydi, ileride biri gecici bir
    hatayi isaretlemeyi unuttugunda hata sessizce kalici sayilir ve yeniden
    deneme hic calismazdi.
    """

    def __init__(self, mesaj: str, gecici: bool | None = None) -> None:
        super().__init__(mesaj)
        self.gecici = gecici


# Beklemek fayda eden durum kodlari: sunucu tarafli veya hiz siniri
GECICI_KODLAR = {408, 409, 425, 429, 500, 502, 503, 504}


@dataclass
class Delta:
    """Stream'den gelen tek parca. Son pakette kullanim bilgisi gelir."""
    content: str = ""
    reasoning: str = ""
    usage: dict | None = None


@dataclass
class Bakiye:
    """Hesabin anlik durumu. Ust seritteki rozet bunu gosterir."""
    tutar: float = 0.0
    birim: str = "USD"
    gecerli: bool = False        # veri gercekten alinabildi mi
    mesaj: str = ""              # alinamadiysa sebep
    zaman: float = 0.0

    @property
    def metin(self) -> str:
        if not self.gecerli:
            return "--"
        simge = {"USD": "$", "CNY": "¥", "TRY": "₺"}.get(self.birim.upper(), "")
        if simge:
            return f"{simge}{self.tutar:,.2f}"
        return f"{self.tutar:,.2f} {self.birim}"

    @property
    def dusuk_mu(self) -> bool:
        return self.gecerli and self.tutar < 1.0


# Bu mesajlar dogrudan sohbet ekranina dusuyor, o yuzden arayuz diline cevrilir.
# Anahtarlar HTTP durum kodu, degerler ceviri tablosundaki Turkce kaynak metin.
HATA_MESAJLARI = {
    400: "İstek geçersiz (400). Model adı veya parametreler hatalı olabilir.",
    401: "API anahtarı geçersiz (401). Ayarlar'dan anahtarı kontrol et.",
    402: "Bakiye yetersiz (402). DeepSeek hesabına kredi yüklemen gerekiyor.",
    403: "Erişim reddedildi (403). Anahtarın bu modele yetkisi yok.",
    404: "Adres bulunamadı (404). Base URL yanlış olabilir.",
    422: "Parametre hatası (422). Sıcaklık veya token değerleri aralığın dışında.",
    429: "Çok fazla istek (429). Birkaç saniye bekleyip tekrar dene.",
    500: "DeepSeek sunucu hatası (500). Biraz sonra tekrar dene.",
    503: "Sunucu meşgul (503). Model şu an aşırı yüklü.",
}


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://api.deepseek.com").rstrip("/")
        self._session = requests.Session()

    # ---------- yardimcilar ----------

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    def _url(self, yol: str) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}{yol}"
        return f"{self.base_url}/v1{yol}"

    def _hata(self, response: requests.Response) -> ApiError:
        ham = HATA_MESAJLARI.get(response.status_code)
        detay = ""
        try:
            govde = response.json()
            detay = (
                govde.get("error", {}).get("message")
                if isinstance(govde.get("error"), dict)
                else str(govde)
            ) or ""
        except Exception:
            detay = (response.text or "")[:300]
        mesaj = t(ham) if ham else f"{t('API hatası')} ({response.status_code})."
        return ApiError(
            f"{mesaj}\n{detay}".strip(),
            gecici=response.status_code in GECICI_KODLAR,
        )

    # ---------- baglanti testi ----------

    def bakiye(self, zaman_asimi: int = 15) -> Bakiye:
        """Kalan bakiyeyi yapisal olarak verir. Hicbir zaman istisna atmaz."""
        import time as _time

        if not self.api_key:
            return Bakiye(mesaj=t("API anahtarı girilmemiş."), zaman=_time.time())
        try:
            resp = self._session.get(
                f"{self.base_url}/user/balance",
                headers=self._headers,
                timeout=zaman_asimi,
            )
        except requests.RequestException as exc:
            return Bakiye(mesaj=f"{t('Bağlantı kurulamadı')}: {exc}", zaman=_time.time())

        if resp.status_code != 200:
            return Bakiye(mesaj=str(self._hata(resp)), zaman=_time.time())

        try:
            veri = resp.json()
            bilgiler = veri.get("balance_infos") or []
            if not bilgiler:
                return Bakiye(mesaj=t("Bakiye bilgisi boş döndü."), zaman=_time.time())
            bilgi = bilgiler[0]
            return Bakiye(
                tutar=float(bilgi.get("total_balance") or 0.0),
                birim=str(bilgi.get("currency") or "USD"),
                gecerli=True,
                zaman=_time.time(),
            )
        except Exception as exc:
            return Bakiye(mesaj=f"{t('Bakiye okunamadı')}: {exc}", zaman=_time.time())

    def test(self) -> str:
        if not self.api_key:
            raise ApiError(t("API anahtarı boş."), gecici=False)
        durum = self.bakiye()
        if durum.gecerli:
            return f"{t('Bağlantı başarılı. Kalan bakiye')}: {durum.metin}"
        raise ApiError(durum.mesaj or t("Bağlantı kurulamadı."), gecici=False)

    # ---------- streaming sohbet ----------

    def models(self) -> list[str]:
        """Anahtarin erisebildigi model listesini ceker."""
        try:
            resp = self._session.get(self._url("/models"), headers=self._headers, timeout=15)
            if resp.status_code != 200:
                return []
            veri = resp.json().get("data") or []
            return [m.get("id") for m in veri if m.get("id")]
        except Exception:
            return []

    def stream(
        self,
        messages: list[dict],
        model: str = "deepseek-v4-flash",
        temperature: float = 0.7,
        max_tokens: int = 16384,
        thinking: bool = True,
        cancel: threading.Event | None = None,
    ) -> Iterator[Delta]:
        if not self.api_key:
            raise ApiError(t("API anahtarı girilmemiş."), gecici=False)

        govde = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            # v4 modellerinde dusunme modu varsayilan acik; acikca belirtiyoruz
            "thinking": {"type": "enabled" if thinking else "disabled"},
            # son pakette token kullanimi gelsin (maliyet hesabi icin)
            "stream_options": {"include_usage": True},
        }

        try:
            resp = self._session.post(
                self._url("/chat/completions"),
                headers=self._headers,
                json=govde,
                stream=True,
                timeout=(20, 300),
            )
        except requests.RequestException as exc:
            raise ApiError(f"{t('Bağlantı hatası')}: {exc}", gecici=True) from None

        if resp.status_code != 200:
            hata = self._hata(resp)
            resp.close()
            raise hata

        try:
            for ham in resp.iter_lines(decode_unicode=True):
                if cancel is not None and cancel.is_set():
                    break
                if not ham:
                    continue
                if not ham.startswith("data:"):
                    continue
                yuk = ham[5:].strip()
                if yuk == "[DONE]":
                    break
                try:
                    paket = json.loads(yuk)
                except json.JSONDecodeError:
                    continue
                kullanim = paket.get("usage")
                if kullanim:
                    yield Delta(usage=kullanim)

                secenekler = paket.get("choices") or []
                if not secenekler:
                    continue
                delta = secenekler[0].get("delta") or {}
                icerik = delta.get("content") or ""
                dusunce = delta.get("reasoning_content") or delta.get("thinking") or ""
                if icerik or dusunce:
                    yield Delta(content=icerik, reasoning=dusunce)
        except requests.RequestException as exc:
            raise ApiError(f"{t('Akış kesildi')}: {exc}", gecici=True) from None
        finally:
            resp.close()
