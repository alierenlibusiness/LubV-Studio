"""Kalici ayarlar: API anahtari, model parametreleri, sistem prompt'u, proje yolu."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "LUBV Studio"
APP_VERSION = "1.0"

APP_DIR = Path.home() / ".lubv_studio"
CONFIG_PATH = APP_DIR / "config.json"
MEMORY_DIR = APP_DIR / "memory"

# DeepSeek'in guncel modelleri. Uygulama acilista /models ucundan gercek
# listeyi de ceker; buradakiler cevrimdisi/hatali durumda yedek listedir.
MODELS = [
    ("deepseek-v4-flash", "V4 Flash  ·  hızlı ve ucuz  ·  1M bağlam"),
    ("deepseek-v4-pro", "V4 Pro  ·  en güçlü  ·  1M bağlam"),
]
KIPLER = {
    "code": (
        "Code",
        "Vibe coding. Dosyaları okur, kod yazar, komut çalıştırır, internete bakar.",
    ),
    "chat": (
        "Chat",
        "Düz sohbet. Hiçbir dosyaya dokunmaz, sadece konuşur ve fikir verir.",
    ),
}

# Arayuz dili ne ise LUBV de o dilde cevap verir; ayri bir ayar yok.
CEVAP_DILI = {
    "tr": (
        "# CEVAP DILI\n"
        "Kullanici hangi dilde yazarsa yazsin, cevaplarini her zaman TURKCE ver. "
        "Ingilizce soru sorsa bile Turkce cevapla. Kod, degisken adlari ve "
        "terminal komutlari elbette kendi dilinde kalir."
    ),
    "en": (
        "# RESPONSE LANGUAGE\n"
        "Always answer in ENGLISH, no matter which language the user writes in. "
        "Even if the user writes in Turkish, reply in English. Code, identifiers "
        "and terminal commands stay as they are."
    ),
}

CHAT_KIPI_TALIMATI = """
# SU AN SOHBET KIPINDESIN
Araclarin kapali. Dosya okuyamaz, yazamaz, komut calistiramaz, internete
bakamazsin. Kullaniciyla normal sohbet et: sorularini cevapla, fikir ver,
kod parcasi istenirse cevabinin icinde ``` blogu olarak goster ama dosyaya
yazmaya calisma. Etiket (FILE_READ, RUN_COMMAND vb.) kullanma, calismazlar.
Bir sey uygulamasi gerekiyorsa kullaniciya "Code kipine gecersen yapabilirim" de.
"""

MODLAR = {
    "plan": (
        "Plan",
        "Sadece okur ve araştırır, hiçbir dosyayı değiştirmez. Önce plan çıkarır.",
    ),
    "onay": (
        "Onaylı",
        "Her dosya değişikliği ve komut için sana sorar. Günlük kullanım için ideal.",
    ),
    "oto": (
        "Otomatik",
        "Sormadan yazar, siler, komut çalıştırır. Hızlıdır, her değişiklik geri alınabilir.",
    ),
}

PLAN_MODU_TALIMATI = """
# SU AN PLAN MODUNDASIN
Hicbir dosyayi degistiremez, silemez, komut calistiramazsin. Sadece
FILE_READ, FILE_LIST, FILE_SEARCH, WEB_SEARCH, WEB_FETCH kullanabilirsin.
Once kodu incele, sonra numarali, net bir uygulama plani sun:
hangi dosyada ne degisecek, neden, hangi sirayla, riskler neler.
Sonunda "Onaylarsan Otomatik/Onayli moda gecip uygulayabilirim." de.
"""

OTO_MODU_TALIMATI = """
# SU AN OTOMATIK MODDASIN
Kullanici her adimda onay vermeyecek. Isi bastan sona kendin bitir:
dosyalari oku, degisiklikleri yap, gerekiyorsa calistirip test et,
hata cikarsa duzelt ve tekrar dene. Ancak geri donusu olmayan
tehlikeli komutlardan (disk formatlama, toplu silme, git push --force)
kacin; boyle bir sey gerekiyorsa once kullaniciya sor.
"""

MODEL_NOTLARI = {
    "deepseek-v4-flash": "Günlük kodlama için ideal. Ucuz, hızlı, 1M token bağlam.",
    "deepseek-v4-pro": "Zor mimari kararlar ve karmaşık refactor için. Daha pahalı.",
}

DEFAULT_SYSTEM_PROMPT = """Sen LUBV'sin, kullanıcının kişisel kodlama asistanı.

Nasıl çalışırsın:
- Türkçe konuşursun, kısa ve net yazarsın.
- Kod yazmadan önce ilgili dosyaları okursun, tahmin etmezsin.
- Küçük değişikliklerde dosyanın sadece ilgili parçasını değiştirirsin.
- İşi bitirdikten sonra ne yaptığını tek paragrafta özetlersin.
- Emin olmadığın bir şey varsa sorarsın, uydurmazsın.

NOT: Bu alan tamamen senin kontrolünde. Kendi LUBV talimatlarını buraya
yapıştırıp Kaydet dediğin anda kalıcı olarak kullanılır. Dosya işlemleri
protokolü bu metnin sonuna otomatik eklenir, onu buraya yazmana gerek yok.
"""


@dataclass
class Config:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 16384
    thinking: bool = True
    language: str = "tr"        # tr | en  (arayuz dili)
    kip: str = "code"           # code | chat
    mode: str = "onay"          # plan | onay | oto  (sadece code kipinde)
    project_root: str = ""
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_iterations: int = 12
    auto_approve_write: bool = False
    auto_approve_command: bool = False
    auto_approve_delete: bool = False
    use_memory: bool = True
    command_timeout: int = 120
    history_limit: int = 30
    show_reasoning: bool = True
    editor_font_size: int = 13
    window_geometry: str = ""
    splitter_state: str = ""
    recent_projects: list = field(default_factory=list)

    # ---------- yukle / kaydet ----------

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                known = {f.name for f in fields(cls)}
                for key, value in raw.items():
                    if key in known:
                        setattr(cfg, key, value)
            except Exception:
                pass  # bozuk config dosyasi varsayilanlari ezmesin
        cfg.ensure_dirs()
        return cfg

    def save(self) -> None:
        self.ensure_dirs()
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(CONFIG_PATH)

    @staticmethod
    def ensure_dirs() -> None:
        for path in (APP_DIR, MEMORY_DIR):
            path.mkdir(parents=True, exist_ok=True)

    # ---------- yardimcilar ----------

    @property
    def project_name(self) -> str:
        if not self.project_root:
            return "proje seçilmedi"
        return Path(self.project_root).name or self.project_root

    def remember_project(self, yol: str) -> None:
        yol = str(Path(yol))
        liste = [p for p in (self.recent_projects or []) if p != yol]
        liste.insert(0, yol)
        self.recent_projects = liste[:8]

    def is_ready(self) -> tuple[bool, str]:
        if not self.api_key.strip():
            return False, "API anahtarı girilmemiş. Ayarlar panelinden ekle."
        if not self.project_root or not Path(self.project_root).is_dir():
            return False, "Geçerli bir proje klasörü seçilmemiş."
        return True, ""
