"""DeepSeek API istemcisi - streaming sohbet, baglanti testi, bakiye/hata mesajlari."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Iterator

import requests


class ApiError(Exception):
    """Kullaniciya gosterilebilir, Turkce aciklamali API hatasi."""


@dataclass
class Delta:
    """Stream'den gelen tek parca. Son pakette kullanim bilgisi gelir."""
    content: str = ""
    reasoning: str = ""
    usage: dict | None = None


HATA_MESAJLARI = {
    400: "Istek gecersiz (400). Model adi veya parametreler hatali olabilir.",
    401: "API anahtari gecersiz (401). Ayarlar'dan anahtari kontrol et.",
    402: "Bakiye yetersiz (402). DeepSeek hesabina kredi yuklemen gerekiyor.",
    403: "Erisim reddedildi (403). Anahtarin bu modele yetkisi yok.",
    404: "Adres bulunamadi (404). Base URL yanlis olabilir.",
    422: "Parametre hatasi (422). Sicaklik veya token degerleri araligin disinda.",
    429: "Cok fazla istek (429). Birkac saniye bekleyip tekrar dene.",
    500: "DeepSeek sunucu hatasi (500). Biraz sonra tekrar dene.",
    503: "Sunucu mesgul (503). Model su an asiri yuklu.",
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
        mesaj = HATA_MESAJLARI.get(response.status_code)
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
        if not mesaj:
            mesaj = f"API hatasi ({response.status_code})."
        return ApiError(f"{mesaj}\n{detay}".strip())

    # ---------- baglanti testi ----------

    def test(self) -> str:
        if not self.api_key:
            raise ApiError("API anahtari bos.")
        try:
            resp = self._session.get(
                f"{self.base_url}/user/balance", headers=self._headers, timeout=20
            )
        except requests.RequestException as exc:
            raise ApiError(f"Baglanti kurulamadi: {exc}") from None
        if resp.status_code == 200:
            try:
                veri = resp.json()
                bilgi = (veri.get("balance_infos") or [{}])[0]
                tutar = bilgi.get("total_balance")
                birim = bilgi.get("currency", "")
                if tutar is not None:
                    return f"Baglanti basarili. Kalan bakiye: {tutar} {birim}"
            except Exception:
                pass
            return "Baglanti basarili."
        raise self._hata(resp)

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
            raise ApiError("API anahtari girilmemis.")

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
            raise ApiError(f"Baglanti hatasi: {exc}") from None

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
            raise ApiError(f"Akis kesildi: {exc}") from None
        finally:
            resp.close()
