# Kurs Manager — Android sinxronizatsiya rejasi

## Maqsad
Cloud/server/domen YO'Q. Telefon va kompyuter to'g'ridan-to'g'ri
(WiFi, hotspot, USB) gaplashadi. Ulanish **bir marta** kod bilan
tasdiqlanadi, keyingi safar **avtomatik** sinxronlashadi.

## Arxitektura

```
[Android ilova] ←→ HTTP (lokal tarmoq) ←→ [Desktop exe]
   Room (SQLite)         8741-port          SQLite + sync moduli
```

## Ulanish turlari
1. **Telefon hotspoti** — telefonda hotspot yoqiladi, kompyuter ulanadi
2. **Bitta WiFi** — ikkalasi bir tarmoqda
3. **USB** — keyinroq (adb reverse orqali)

## Bir martalik ulash (pairing)
1. Kompyuterda **"Telefon ulash"** tugmasi → 4 xonali kod + kompyuter IP chiqadi
2. Telefonda **"Kompyuterga ulash"** → IP yoziladi (yoki avtomatik topiladi),
   kod teriladi
3. Kompyuter qurilmani eslab qoladi (token beriladi)
4. Keyingi safar: telefon tanish kompyuterni ko'rsa — **so'ramasdan** ulanib,
   **"Sinxronlash"** bilan almashadi

## Sinxronizatsiya qoidalari (hech nima o'chmaydi)
- Har bir yozuvda `updated_at` (oxirgi o'zgarish vaqti) bo'ladi
- O'chirish — `tombstones` jadvaliga yoziladi (qattiq o'chirish sinxronlanmaydi,
  qayta "tirilish" bo'lmaydi)
- Konflikt: `updated_at` kechroq bo'lgani yutadi (qator darajasi)
- Har bir o'zgarish alohida `upsert` — butun jadval almashtirilmaydi
- Telefon offline ishlaydi, navbatda (outbox) saqlaydi, aloqa chiqishi bilan yuboradi

## Xavfsizlik
- Faqat juftlangan tokenlar qabul qilinadi
- Token tasodifiy (32 bayt), har qurilmaga alohida
- Juftlash oynasi yopilganda kod kuchini yo'qotadi (5 daqiqa)

## Bosqichlar
- [x] 1. Hujjat + protokol (shu papka)
- [x] 2. `trusted_devices` + `tombstones` modellari (create_all avtomatik yaratadi)
- [x] 3. Barcha sinxron jadvallarga `updated_at` ustuni + touch/tomb (26 test o'tdi)
- [x] 4. `pairing_service` (kod + token, sinovdan o'tdi)
- [x] 5. Desktop: sync HTTP server + "Telefon ulash" oynasi (10 test o'tdi)
- [x] 6. `sync_service` (push/pull, merge)
- [x] 7. Android loyiha skeleti (`android_versiya/app/`) — Native Kotlin + Room, 7 ekran
- [x] 8. Emulyatorda test: pairing + ikki tomonlama sync ✅ (05.10.2026)
- [x] 9. Topilgan bug'lar tuzatildi: server nom-adoptatsiya + telefon retry-safe outbox + deletes alohida array
- [x] 10. Exe rebuild ✅ (sync server + nom-adoptatsiya ichida, smoke: 8741 port eshitilmoqda)
- [x] 11. Telefon formasi to'ldirildi (08.10.2026):
  - "Yangi o'quvchi" → **F.I.Sh, Sinf (7–11), Kelgan sana (kalendar)** — `created_at` ga yoziladi,
    exe'dagi "Kelgan sana" ustuni va to'lov jadvali shundan foydalanadi
  - Davomat ekrani → **"Davomatni saqlash"** tugmasi: lokal saqlash + darhol 8741'ga push
    (chekdosh `app().sync.fullSync()`, 30 daqiqalik avto-sinxron ham ishlaydi)
  - APK qayta yig'ildi: `app/app/build/outputs/apk/debug/app-debug.apk`
  - E2E test (telefon → 8741 → exe bazasi → `student_service`/`attendance_service`): **11/11 OK**
- [x] 12. Ikkala yo'nalishli sinxron ta'minlandi va tekshirildi (08.10.2026, **21/21 OK**):
  - Telefon → exe: courses, students (sinf/kelgan sana), attendance, monthly_payments,
    payments, test_results, reminders — hammasi qo'llanadi va exe ekranlarida ko'rinadi
  - exe → telefon: yangi o'quvchi qo'shish, davomat ✓/✗, oylik to'lov ✓ (to'lov holati
    `paid`/`unpaid` bilan birga), o'chirish (tombstone) — telefonga qaytadi
  - Konflikt: eskiri `updated_at` push **skip**, yangisi **yutadi**; o'chirilgan qator
    tombstone tufayli qayta tirilmaydi
  - Wire qoidasi tekshirildi: `id`/chet-kalitlar yuborilmaydi, o'rniga `*_uid`
  - Exe qayta build qildi: `dist/KursManager.exe` (71 MB, 21:40) — smoke: 8741 ochiladi,
    `GET /sync/hello` → `{"app":"KursManager","version":"1.3.5",...}`
