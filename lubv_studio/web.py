"""Internet erisimi: anahtarsiz web aramasi (DuckDuckGo) ve sayfa metnini cekme.

Hicbir API anahtari gerektirmez. LUBV guncel dokumantasyona, hata mesajlarina
ve kutuphane surumlerine buradan bakar.
"""

from __future__ import annotations

import html as html_mod
import re
import urllib.parse

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 25
MAX_TEXT = 18000


# --------------------------------------------------------------------------
# Arama
# --------------------------------------------------------------------------

_LITE_ROW_RE = re.compile(
    r'<a[^>]+class="result-link"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'.*?class="result-snippet"[^>]*>(?P<snippet>.*?)</td>',
    re.DOTALL | re.IGNORECASE,
)
_HTML_ROW_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'(?:.*?class="result__snippet"[^>]*>(?P<snippet>.*?)</a>)?',
    re.DOTALL | re.IGNORECASE,
)


def _temizle(parca: str) -> str:
    metin = re.sub(r"<[^>]+>", "", parca or "")
    metin = html_mod.unescape(metin)
    return re.sub(r"\s+", " ", metin).strip()


def _gercek_url(ham: str) -> str:
    ham = html_mod.unescape(ham or "")
    if ham.startswith("//"):
        ham = "https:" + ham
    if "duckduckgo.com/l/" in ham or "uddg=" in ham:
        try:
            sorgu = urllib.parse.urlparse(ham).query
            hedef = urllib.parse.parse_qs(sorgu).get("uddg", [None])[0]
            if hedef:
                return urllib.parse.unquote(hedef)
        except Exception:
            pass
    return ham


_RSS_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL | re.IGNORECASE)


def _rss_alan(parca: str, ad: str) -> str:
    es = re.search(rf"<{ad}>(.*?)</{ad}>", parca, re.DOTALL | re.IGNORECASE)
    if not es:
        return ""
    icerik = es.group(1)
    cdata = re.match(r"\s*<!\[CDATA\[(.*?)\]\]>\s*$", icerik, re.DOTALL)
    if cdata:
        icerik = cdata.group(1)
    return _temizle(icerik)


def _bing_rss(sorgu: str, limit: int) -> list[tuple[str, str, str]]:
    """Bing'in RSS ciktisi - anahtarsiz, kararli ve hizli."""
    cevap = requests.get(
        "https://www.bing.com/search",
        params={"q": sorgu, "format": "rss", "count": max(limit, 10)},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    if cevap.status_code != 200:
        raise requests.RequestException(f"HTTP {cevap.status_code}")
    cevap.encoding = "utf-8"

    sonuclar: list[tuple[str, str, str]] = []
    for parca in _RSS_ITEM_RE.findall(cevap.text):
        baslik = _rss_alan(parca, "title")
        url = _rss_alan(parca, "link")
        ozet = _rss_alan(parca, "description")
        if baslik and url.startswith("http"):
            sonuclar.append((baslik, url, ozet))
        if len(sonuclar) >= limit:
            break
    return sonuclar


def _bicimle(sorgu: str, sonuclar: list[tuple[str, str, str]]) -> str:
    satirlar = [f"'{sorgu}' icin {len(sonuclar)} sonuc:\n"]
    for no, (baslik, url, ozet) in enumerate(sonuclar, 1):
        satirlar.append(f"{no}. {baslik}\n   {url}")
        if ozet:
            satirlar.append(f"   {ozet[:400]}")
    satirlar.append("\nDetay gerekiyorsa <WEB_FETCH> ile ilgili adresi ac ve oku.")
    return "\n".join(satirlar)


def _ddgs(sorgu: str, limit: int) -> list[tuple[str, str, str]]:
    """ddgs kutuphanesi - DuckDuckGo'nun bot korumasini dogru sekilde asar."""
    from ddgs import DDGS  # yerel import: kutuphane yoksa yedege dusulur

    ham = DDGS().text(sorgu, max_results=limit)
    sonuclar: list[tuple[str, str, str]] = []
    for kayit in ham or []:
        baslik = _temizle(kayit.get("title") or "")
        url = (kayit.get("href") or kayit.get("url") or "").strip()
        ozet = _temizle(kayit.get("body") or kayit.get("description") or "")
        if baslik and url.startswith("http"):
            sonuclar.append((baslik, url, ozet))
    return sonuclar


def search(sorgu: str, limit: int = 6) -> tuple[bool, str]:
    """Web aramasi yapar, sonuclari duz metin olarak dondurur.

    Sirasiyla ddgs -> Bing RSS -> ham DuckDuckGo denenir; biri tutunca doner.
    """
    sorgu = (sorgu or "").strip()
    if not sorgu:
        return False, "Bos arama sorgusu."

    son_hata = ""

    # 1) ddgs (en iyi sonuc kalitesi)
    try:
        sonuclar = _ddgs(sorgu, limit)
        if sonuclar:
            return True, _bicimle(sorgu, sonuclar)
        son_hata = "ddgs sonuc dondurmedi"
    except ImportError:
        son_hata = "ddgs kurulu degil (pip install ddgs)"
    except Exception as exc:
        son_hata = f"ddgs: {exc}"

    # 2) Bing RSS
    try:
        sonuclar = _bing_rss(sorgu, limit)
        if sonuclar:
            return True, _bicimle(sorgu, sonuclar)
    except Exception as exc:
        son_hata = f"{son_hata}; bing: {exc}"

    # 2) DuckDuckGo yedegi
    basliklar = {"User-Agent": USER_AGENT, "Accept-Language": "tr,en;q=0.8"}
    kaynaklar = [
        ("https://lite.duckduckgo.com/lite/", _LITE_ROW_RE),
        ("https://html.duckduckgo.com/html/", _HTML_ROW_RE),
    ]

    for adres, desen in kaynaklar:
        try:
            cevap = requests.post(
                adres, data={"q": sorgu}, headers=basliklar, timeout=TIMEOUT
            )
            if cevap.status_code != 200:
                son_hata = f"{adres} -> HTTP {cevap.status_code}"
                continue
            sonuclar = []
            for eslesme in desen.finditer(cevap.text):
                baslik = _temizle(eslesme.group("title"))
                url = _gercek_url(eslesme.group("url"))
                ozet = _temizle(eslesme.groupdict().get("snippet") or "")
                if not baslik or not url.startswith("http"):
                    continue
                sonuclar.append((baslik, url, ozet))
                if len(sonuclar) >= limit:
                    break
            if sonuclar:
                return True, _bicimle(sorgu, sonuclar)
            son_hata = "sonuc ayristirilamadi"
        except requests.RequestException as exc:
            son_hata = str(exc)
            continue

    return False, f"Arama basarisiz ({son_hata}). Internet baglantisini kontrol et."


# --------------------------------------------------------------------------
# Sayfa okuma
# --------------------------------------------------------------------------

_SCRIPT_RE = re.compile(r"<(script|style|noscript|svg|head)[^>]*>.*?</\1>", re.DOTALL | re.I)
_BLOCK_RE = re.compile(r"</(p|div|section|article|li|tr|h[1-6]|pre|br)\s*>", re.I)


def fetch(url: str) -> tuple[bool, str]:
    """Bir sayfayi indirir ve okunabilir duz metne cevirir."""
    url = (url or "").strip().strip("<>").strip()
    if not url:
        return False, "Bos adres."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        cevap = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "tr,en;q=0.8"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return False, f"Sayfa acilamadi: {exc}"

    if cevap.status_code != 200:
        return False, f"HTTP {cevap.status_code} - sayfa alinamadi."

    tur = cevap.headers.get("Content-Type", "")
    govde = cevap.text

    if "json" in tur:
        return True, govde[:MAX_TEXT]

    if "html" not in tur and "xml" not in tur and "text" not in tur:
        return False, f"Desteklenmeyen icerik turu: {tur}"

    baslik_es = re.search(r"<title[^>]*>(.*?)</title>", govde, re.DOTALL | re.I)
    baslik = _temizle(baslik_es.group(1)) if baslik_es else ""

    temiz = _SCRIPT_RE.sub(" ", govde)
    temiz = re.sub(r"<!--.*?-->", " ", temiz, flags=re.DOTALL)
    temiz = _BLOCK_RE.sub("\n", temiz)
    temiz = re.sub(r"<[^>]+>", " ", temiz)
    temiz = html_mod.unescape(temiz)
    temiz = re.sub(r"[ \t\xa0]+", " ", temiz)
    temiz = re.sub(r"\n\s*\n\s*\n+", "\n\n", temiz)
    temiz = "\n".join(satir.strip() for satir in temiz.splitlines())
    temiz = temiz.strip()

    if len(temiz) > MAX_TEXT:
        temiz = temiz[:MAX_TEXT] + "\n\n... (sayfa uzun oldugu icin kirpildi)"

    ust = f"KAYNAK: {cevap.url}\n"
    if baslik:
        ust += f"BASLIK: {baslik}\n"
    return True, ust + "\n" + (temiz or "(sayfada okunabilir metin bulunamadi)")
