"""Arayuz dili: Turkce / English.

Anahtar olarak Turkce metnin kendisi kullanilir; boylece kodda ne yazdigi
okununca anlasilir ve ceviri bulunamazsa Turkce'ye duser.

Kullanim:
    from .i18n import t
    QLabel(t("Dosyalar"))
"""

from __future__ import annotations

DILLER = {"tr": "Türkçe", "en": "English"}

_AKTIF = "tr"

EN: dict[str, str] = {
    # ---- genel / ray ----
    "Dosyalar": "Files",
    "Kaynak kontrol ve GitHub": "Source control and GitHub",
    "Bellek": "Memory",
    "Beyin, sistem prompt": "Brain, system prompt",
    "Beyin": "Brain",
    "Geri al": "Undo",
    "Ayarlar ve harcama": "Settings and spending",
    "Ayarlar": "Settings",
    "AYARLAR": "SETTINGS",

    # ---- dosya paneli ----
    "Ağacı yenile": "Refresh tree",
    "Başka proje klasörü aç": "Open another project folder",
    "dosya adı filtrele": "filter file name",
    "Seçili dosyayı sohbete ekle": "Add selected file to chat",
    "Proje klasörünü seç": "Choose project folder",
    "Proje açıldı: ": "Project opened: ",
    "Açılamadı (ikili veya çok büyük dosya): ": "Cannot open (binary or too large): ",

    # ---- bellek paneli ----
    "LUBV'nin sohbetler arası hatırladıkları. Buradaki her not "
    "istek başına sistem prompt'una eklenir.":
        "What LUBV remembers between chats. Every note here is added to the "
        "system prompt on each request.",
    "Listeyi yenile": "Refresh list",
    "yeni not, Enter ile ekle": "new note, press Enter to add",
    "Bu proje": "This project",
    "Her yerde": "Everywhere",
    "Seçiliyi sil": "Delete selected",
    "Projeyi boşalt": "Clear project",
    "Bu projeye ait tüm notlar silinsin mi?": "Delete all notes for this project?",
    "Henüz not yok.": "No notes yet.",
    "genel": "global",
    "proje": "project",
    "Bellek güncellendi.": "Memory updated.",

    # ---- beyin paneli ----
    "LUBV'nin sistem prompt'u. Kendi talimatlarını buraya yapıştır ve "
    "Kaydet'e bas, kalıcı olur. Araç protokolü sona otomatik eklenir.":
        "LUBV's system prompt. Paste your own instructions here and press Save; "
        "they persist. The tool protocol is appended automatically.",
    "Kaydet": "Save",
    "Sıfırla": "Reset",
    "Beyin kaydedildi, bir sonraki mesajdan itibaren geçerli.":
        "Brain saved, effective from the next message.",
    " karakter  ·  ~": " characters  ·  ~",
    " satır": " lines",

    # ---- geri al paneli ----
    "LUBV'nin değiştirdiği her dosyanın önceki hali burada. "
    "Bir satıra çift tıkla, o değişiklik geri alınsın.":
        "The previous version of every file LUBV touched is kept here. "
        "Double click a row to revert that change.",
    "Seçiliyi geri al": "Revert selected",
    "Henüz bir değişiklik yok.": "No changes yet.",
    "geri alındı": "reverted",
    "Geri alınamadı: ": "Could not revert: ",
    "yazma": "write",
    "düzenleme": "edit",
    "silme": "delete",

    # ---- ayarlar ----
    "DeepSeek API": "DeepSeek API",
    "Göster": "Show",
    "Gizle": "Hide",
    "Bağlantıyı test et ve bakiyeyi göster": "Test connection and show balance",
    "Bağlantı test ediliyor": "Testing connection",
    "Bağlantı başarısız": "Connection failed",
    "Bağlantı başarısız.": "Connection failed.",
    "Model": "Model",
    "Düşünme modu": "Thinking mode",
    "Daha isabetli cevap, biraz daha yavaş ve pahalı":
        "More accurate answers, a bit slower and pricier",
    "Düşünme akışını sohbette göster": "Show thinking stream in chat",
    "Sıcaklık  ": "Temperature  ",
    "Maks. yanıt token": "Max response tokens",
    "Maks. ajan adımı": "Max agent steps",
    "Bir istek için LUBV'nin arka arkaya kaç adım atabileceği.":
        "How many steps LUBV may take in a row for one request.",
    "İzinler": "Permissions",
    "İZİNLER": "PERMISSIONS",
    "Dosya yazmayı sorma": "Do not ask before writing files",
    "Dosya silmeyi sorma": "Do not ask before deleting files",
    "Komut çalıştırmayı sorma": "Do not ask before running commands",
    "Kalıcı belleği kullan": "Use persistent memory",
    "Komut zaman aşımı (sn)": "Command timeout (s)",
    "Harcama": "Spending",
    "HARCAMA": "SPENDING",
    "Oturum sayacını sıfırla": "Reset session counter",
    "API anahtarı kaydedildi.": "API key saved.",
    "BU OTURUM": "THIS SESSION",
    "BUGÜN": "TODAY",
    "TOPLAM": "TOTAL",
    "SON GÜNLER": "RECENT DAYS",
    " token, ": " tokens, ",
    " istek": " requests",
    "Arayüz dili": "Interface language",
    "Dil değişikliği": "Language change",
    "Dil değiştirildi. Uygulama şimdi yeniden başlatılsın mı?":
        "Language changed. Restart the application now?",

    # ---- sohbet ----
    "LUBV'ye ne yapmasını istiyorsun?": "What do you want LUBV to do?",
    "Ne konuşmak istersin?": "What would you like to talk about?",
    "Enter gönderir, Shift+Enter alt satıra geçer":
        "Enter sends, Shift+Enter adds a new line",
    "Gönder  (Enter)": "Send  (Enter)",
    "Durdur  (Esc)": "Stop  (Esc)",
    "Modeli Ayarlar panelinden değiştirebilirsin":
        "You can change the model in the Settings panel",
    "Yeni sohbet, geçmişi temizler": "New chat, clears history",
    "Yeni sohbet başladı.": "New chat started.",
    "Ne yapmamı istiyorsan aşağıya yaz": "Type below what you want me to do",
    "Bağlama eklendi: ": "Added to context: ",
    "Kaldırmak için tıkla": "Click to remove",
    "yanıtlıyor": "answering",
    "adım ": "step ",
    " modu": " mode",
    "API anahtarı girilmemiş. Ayarlar panelinden ekle.":
        "No API key. Add one from the Settings panel.",
    "API anahtarı girilmemiş. Ayarlar sekmesinden ekle.":
        "No API key. Add one from the Settings tab.",
    "Geçerli bir proje klasörü seçilmemiş.": "No valid project folder selected.",
    "Bu tür işlemler artık sorulmadan yapılacak.":
        "This kind of action will no longer be asked about.",
    "proje seçilmedi": "no project selected",

    # ---- kipler ve modlar ----
    "Vibe coding. Dosyaları okur, kod yazar, komut çalıştırır, internete bakar.":
        "Vibe coding. Reads files, writes code, runs commands, searches the web.",
    "Düz sohbet. Hiçbir dosyaya dokunmaz, sadece konuşur ve fikir verir.":
        "Plain chat. Touches no files, just talks and gives ideas.",
    "Plan": "Plan",
    "Onaylı": "Approve",
    "Otomatik": "Auto",
    "Sadece okur ve araştırır, hiçbir dosyayı değiştirmez. Önce plan çıkarır.":
        "Only reads and researches, changes nothing. Produces a plan first.",
    "Her dosya değişikliği ve komut için sana sorar. Günlük kullanım için ideal.":
        "Asks you before every file change and command. Ideal for daily use.",
    "Sormadan yazar, siler, komut çalıştırır. Hızlıdır, her değişiklik geri alınabilir.":
        "Writes, deletes and runs without asking. Fast, and every change is revertible.",

    # ---- modeller ----
    "V4 Flash  ·  hızlı ve ucuz  ·  1M bağlam": "V4 Flash  ·  fast and cheap  ·  1M context",
    "V4 Pro  ·  en güçlü  ·  1M bağlam": "V4 Pro  ·  most capable  ·  1M context",
    "Günlük kodlama için ideal. Ucuz, hızlı, 1M token bağlam.":
        "Ideal for everyday coding. Cheap, fast, 1M token context.",
    "Zor mimari kararlar ve karmaşık refactor için. Daha pahalı.":
        "For hard architecture calls and complex refactors. Pricier.",

    # ---- arac kartlari ----
    "Dosya okundu": "File read",
    "Dosya yazıldı": "File written",
    "Dosya düzenlendi": "File edited",
    "Klasör listelendi": "Folder listed",
    "Projede arandı": "Searched in project",
    "Dosya silindi": "File deleted",
    "Komut çalıştırıldı": "Command executed",
    "İnternette arandı": "Searched the web",
    "Sayfa okundu": "Page read",
    "Belleğe yazıldı": "Written to memory",
    "çalışıyor": "running",
    "reddedildi": "denied",
    "hata": "error",
    "Ayrıntıyı aç/kapa": "Toggle details",
    "Düşünüyor": "Thinking",
    "Düşündü": "Thought",
    " kelime": " words",

    # ---- onay diyalogu ----
    "LUBV izin istiyor": "LUBV needs permission",
    "Dosyanın tamamı değiştirilecek": "The whole file will be replaced",
    "Dosyada değişiklik yapılacak": "The file will be modified",
    "Dosya silinecek": "The file will be deleted",
    "Terminal komutu çalıştırılacak": "A terminal command will run",
    "İşlem onayı": "Action approval",
    "Reddet": "Reject",
    "Onayla": "Approve",
    "Bu tür için hep onayla": "Always approve this kind",
    "Bu oturumda bir daha sorulmaz (Ayarlar'dan geri alabilirsin)":
        "You will not be asked again this session (revert it in Settings)",
    "İçerik aynı, değişiklik yok.": "Content is identical, no change.",

    # ---- terminal ve git ----
    "TERMINAL": "TERMINAL",
    "Temizle": "Clear",
    "Ekrandaki çıktıyı siler": "Clears the output on screen",
    "Yeniden başlat": "Restart",
    "Çalışan komutu keser ve kabuğu yeniden başlatır":
        "Stops the running command and restarts the shell",
    "komut yaz ve Enter'a bas, örnek: git status":
        "type a command and press Enter, e.g. git status",
    "PowerShell oturumu açıldı": "PowerShell session started",
    "PowerShell başlatılamadı.": "PowerShell could not start.",
    "Terminal hazır değil. Önce proje klasörü seç.":
        "Terminal is not ready. Choose a project folder first.",
    "Proje klasörü yok.": "No project folder.",
    "KAYNAK KONTROL": "SOURCE CONTROL",
    "commit mesajı": "commit message",
    "önce bir commit mesajı yaz": "write a commit message first",
    "Commit": "Commit",
    "Push": "Push",
    "Pull": "Pull",
    "Yenile": "Refresh",
    "Geçmiş": "History",
    "Depo kur": "Init repo",
    "git init ve ilk commit": "git init and first commit",
    "GITHUB": "GITHUB",
    "Uzak depoyu bağla ve gönder": "Connect remote and push",
    "Git bulunamadı. https://git-scm.com adresinden kur.":
        "Git not found. Install it from https://git-scm.com",
    "bu klasör bir git deposu değil": "this folder is not a git repository",
    "Bu klasörde depo yok. Aşağıdan 'Depo kur' de.":
        "No repository here. Use 'Init repo' below.",
    "Değişiklik yok, her şey temiz": "No changes, everything is clean",
    "Bu klasörde git deposu yok.": "No git repository in this folder.",
    "Bağla ve gönder": "Connect and push",
    "Var olan bir depoya bağlanır ve projeyi gönderir":
        "Connects to an existing repository and pushes the project",
    "GitHub'da repo aç": "Create repo on GitHub",
    "Yeni bir depo oluşturur ve projeyi gönderir":
        "Creates a new repository and pushes the project",
    "GitHub hesabı: ": "GitHub account: ",
    "GitHub CLI kurulu değil, repo adresini elle yapıştır":
        "GitHub CLI is not installed, paste the repository URL yourself",
    "GitHub CLI kurulu ama giriş yapılmamış":
        "GitHub CLI is installed but not signed in",
    "GitHub CLI kurulu ama giriş yapılmamış. Giriş başlatılsın mı?":
        "GitHub CLI is installed but not signed in. Start the sign-in flow?",
    "Geçerli bir depo adresi yaz. Örnek: kullanici/repo":
        "Enter a valid repository address. Example: user/repo",
    "Uygulama içinden repo açmak için GitHub CLI gerekiyor "
    "(cli.github.com). Şimdi tarayıcıda yeni repo sayfasını "
    "açayım mı? Sonra adresi yukarıdaki kutuya yapıştır.":
        "Creating a repository from inside the app needs the GitHub CLI "
        "(cli.github.com). Open the new-repository page in your browser "
        "instead? Then paste the address into the box above.",
    "Depo adı:": "Repository name:",
    "Depo herkese açık (public) olsun mu? Hayır dersen özel (private) olur.":
        "Should the repository be public? Choosing No makes it private.",
    "Git kimliği": "Git identity",
    "Commit'lerde görünecek isim:": "Name shown on commits:",
    "Commit'lerde görünecek e-posta:": "Email shown on commits:",
    "Kimlik kaydedilemedi, terminalden dene.":
        "Could not save the identity, try from the terminal.",
    "PowerShell oturumu açıldı": "PowerShell session started",
    "PowerShell başlatılamadı.": "PowerShell could not start.",
    "Terminal hazır değil. Önce proje klasörü seç.":
        "Terminal is not ready. Choose a project folder first.",
    "depo yok": "no repo",
    "uzak depo yok": "no remote",
    "dal: ": "branch: ",

    # ---- editor / karsilama ----
    "DeepSeek ile vibe coding stüdyosu": "Vibe coding studio powered by DeepSeek",
    "Soldan bir dosya seç ve aç  ·  Sağdaki sohbete ne istediğini yaz":
        "Pick a file on the left  ·  Tell the chat on the right what you need",
    "Ctrl+S kaydeder  ·  Ctrl+J terminali açar  ·  Ctrl+B dosya panelini gizler":
        "Ctrl+S saves  ·  Ctrl+J toggles terminal  ·  Ctrl+B hides the file panel",
    "Kaydedildi: ": "Saved: ",
    " dosya kaydedildi.": " files saved.",
    "Kaydedilmemiş değişiklikler": "Unsaved changes",
    "Kaydedilmemiş dosyalar var. Kaydedilsin mi?":
        "There are unsaved files. Save them?",
    "Sa ": "Ln ",
    ", Sü ": ", Col ",
    "oturum ": "session ",
    "bugün ": "today ",
    "SEN": "YOU",
}


def ayarla(dil: str) -> None:
    global _AKTIF
    _AKTIF = dil if dil in DILLER else "tr"


def aktif() -> str:
    return _AKTIF


def t(metin: str) -> str:
    """Turkce metni aktif dile cevirir; karsiligi yoksa oldugu gibi doner."""
    if _AKTIF == "tr":
        return metin
    return EN.get(metin, metin)
