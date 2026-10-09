# Kurs Manager

O'qituvchi uchun o'quvchilar, kurslar va to'lovlarni boshqarish tizimi.
Windows'da ishlaydigan **offline** desktop dastur. Internet/server/cloud talab qilinmaydi —
barcha ma'lumotlar lokal **SQLite** (``kurs_manager.db``) bazasida saqlanadi.

## Texnologiyalar

- Python 3.12+
- PySide6 — native Windows GUI (exe)
- Flask + Bootstrap 5 — web versiya (localhost)
- SQLAlchemy 2.0 — SQLite bilan ishlash
- reportlab — PDF hisobot
- PyInstaller — `KursManager.exe` build

## Ikkita versiya

| | Desktop (exe) | Web (localhost) |
|---|---|---|
| Ishga tushirish | `dist/KursManager.exe` | `python web/app.py` → http://127.0.0.1:5000 |
| Bo'limlar | Bosh sahifa, O'quvchilar, To'lovlar, Test natijalari, Davomat, Eslatmalar, Hisobotlar, Sozlamalar | Bosh sahifa, Ro'yxatga olish, To'lovlar, Test natijalari, Davomat, Eslatmalar, Hisobotlar |
| Bildirishnoma | Windows tray + tovush | Brauzer notification + tovush + toast |
| Database | Ikkalasi ham bir xil `kurs_manager.db` ni ishlatadi | |

## Mavzu (kunduzgi/tungi)

- Web: topbar'dagi 🌙/☀️ tugma (brauzerda saqlanadi)
- Desktop: sidebar'dagi 🌙/☀️ tugma (bazada saqlanadi, qayta ochilganda eslab qolinadi)
- Ro'yxatga olish formasi har doim qora dizaynda

## Masofaviy yangilanish (mijozlar qayta o'rnatmaydi)

1. GitHub'da repo oching (masalan `kurs-manager-updates`), `updates.json` qo'ying:
   ```json
   {
     "win10": {"version": "1.1.0", "url": "https://github.com/.../KursManager.exe",
               "sha256": "...", "notes": "- Yangiliklar ro'yxati"},
     "win8": {"version": "1.1.0", "url": "https://github.com/.../KursManager_Win8.exe",
              "sha256": "...", "notes": "..."}
   }
   ```
2. Har exe'ni GitHub **Releases**'ga yuklang, SHA256 ni hisoblang:
   `certutil -hashfile KursManager.exe SHA256`
3. `services/update_service.py` dagi `DEFAULT_UPDATE_URL` ni o'z `updates.json`
   manzilingizga almashtiring (yoki bazadagi `update_url` sozlamasi orqali).
4. `version.py` dagi `VERSION` ni oshiring va exe'larni qayta yig'ing.
5. Mijoz dasturini ochganda (internet bo'lsa) "Yangi versiya mavjud" so'rovi
   chiqadi → yuklaydi → o'zi almashadi → qayta ochiladi. Eski exe `.bak` da qoladi.

## Funksiyalar

- O'quvchilar CRUD + shaxsiy to'lov miqdori (fee)
- To'lov muddati: har bir o'quvchi o'z ro'yxat sanasidan oylik hisob (1-dek → 31-dek), avtomatik push-eslatma
- Test natijalari: mavzu + savollar + to'g'ri javoblar → foiz + baho avtomatik
- Davomat: haftalik jurnal (✓/✗), tez qo'shish (faqat F.I.Sh)
- Eslatmalar: sana+vaqt → push-habar + tovush
- Hisobotlar: PDF/CSV eksport, backup/restore (exe'da Sozlamalar)

## Loyiha tuzilishi

```
kurs_uchun_dastur/
├── main.py                     # ishga tushirish nuqtasi
├── requirements.txt
├── KursManager.spec            # PyInstaller spec (onefile build)
├── database/
│   ├── database.py             # engine/session/data papka (PDF path)
│   └── models.py               # students, courses, payments, settings
├── services/
│   ├── student_service.py      # o'quvchilar CRUD + stats
│   ├── course_service.py       # kurslar CRUD
│   ├── payment_service.py      # to'lovlar tarixi
│   ├── report_service.py       # hisobotlar + CSV eksport
│   ├── backup_service.py       # backup/restore
│   └── demo_data.py            # demo (test) ma'lumotlar
├── ui/
│   ├── main_window.py          # sidebar + sahifalar
│   ├── theme.py                # dark professional dizayn
│   ├── widgets.py              # qayta ishlatiladigan komponentlar
│   ├── dialogs.py              # formalar va tasdiqlash oynalari
│   ├── dashboard.py            # Bosh sahifa
│   ├── students.py             # O'quvchilar
│   ├── payments.py             # To'lovlar
│   ├── courses.py              # Kurslar
│   ├── reports.py              # Hisobotlar
│   └── settings.py             # Sozlamalar (backup/restore)
├── utils/
│   ├── validators.py           # formalar tekshiruvi
│   ├── logging_config.py       # log tizimi
│   └── branding.py             # ikonka generatsiyasi
├── tools/make_icon.py          # .ico ikonka generatsiyasi
└── dist/KursManager.exe        # TAYYOR DASTUR
```

## 1. Ishga tushirish (development)

```bash
pip install -r requirements.txt
python main.py
```

Birinchi ishga tushishda `kurs_manager.db` avtomatik yaratiladi va 28 ta
demo o'quvchi + 4 ta kurs yuklanadi (o'chirish uchun: Sozlamalar → Demoni
qayta yuklash yoki faylni o'chirish).

## 2. Test qilish

```bash
# Smoke test — oyna ochilib 3 soniyada avtomatik yopiladi
python main.py --smoke

# Offscreen tez tekshiruv (GUI ko'rsatmasdan)
$env:QT_QPA_PLATFORM="offscreen"; python main.py --smoke
```

Qo'lda tekshirish ro'yxati:

- [ ] Dastur Windows'da ochiladi
- [ ] SQLite database ishlaydi (`kurs_manager.db`)
- [ ] Yangi o'quvchi qo'shiladi (📚 Kurslar bo'limida kamida 1 kurs bo'lishi kerak)
- [ ] O'quvchi tahrirlanadi / o'chiriladi (o'chirish oldidan tasdiq dialog)
- [ ] Kurs qo'shiladi / faollashtiriladi / o'chiriladi
- [ ] To'lov holati 🟢/🟡/🔴 tugmalar orqali o'zgaradi
- [ ] Dashboard statistikasi avtomatik yangilanadi
- [ ] Qidiruv + filtr ishlaydi
- [ ] Hisobotlar + CSV eksport ishlaydi
- [ ] Backup yaratish / Backup'dan tiklash ishlaydi
- [ ] Internet talab qilinmaydi

## 3. `.exe` yaratish

Ikonkani generatsiya qilish (1-marta):

```bash
python tools/make_icon.py
```

Build:

```bash
pip install pyinstaller
python -m PyInstaller KursManager.spec --noconfirm
```

## 4. Tayyor dastur qayerda?

```
C:\Users\HP Victus\OneDrive\Desktop\kurs_uchun_dastur\dist\KursManager.exe
```

`KursManager.exe` — bitta fayl (onefile). Boshqa Windows kompyuterga
Python o'rnatmasdan ko'chirib olib ishlatsa bo'ladi.

- Ma'lumotlar bazasi `.exe` turgan papkada `kurs_manager.db` nomi bilan
  avtomatik yaratiladi.
- Agar `.exe` papkasi yozishga ruxsat bermasa (masalan Program Files),
  bazasi `%LOCALAPPDATA%\KursManager\` ga saqlanadi.
- Log fayli ham xuddi shu joyda `kurs_manager.log` sifatida saqlanadi.