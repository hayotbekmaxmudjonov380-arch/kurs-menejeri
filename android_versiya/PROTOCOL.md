# Sync protokoli v1 (HTTP + JSON, 8741-port)

Barcha so'rovlar sarlavhada token yuboradi (juftlashdan keyingilari):
```
X-Device-Token: <32-bayt-hex>
```

## Juftlash (tokensiz)

### GET /sync/hello
Kompyuterni topish. Javob:
```json
{"app": "KursManager", "version": "1.3.15", "sync": 1,
 "needs_pairing": true, "server_time": "<ISO-vaqt>"}
```

### POST /sync/pair
```json
{"device_id": "<telefon-uuid>", "device_name": "Farxod-A52", "code": "4821"}
```
To'g'ri bo'lsa:
```json
{"ok": true, "token": "<32-bayt-hex>"}
```
Xato bo'lsa: `{"ok": false, "error": "..."}` (403)

## Sinxron (token shart)

### GET /sync/changes?since=<ISO-vaqt>&device_id=<uuid>
Shu vaqtdan keyingi o'zgarishlar (since bo'sh — barchasi):
```json
{"changes": [
  {"table": "students", "uid": "<32-hex>", "updated_at": "...",
   "deleted": false, "row": {...}}
],
 "deleted": [
  {"table": "students", "row_id": 7, "uid": "<32-hex>", "deleted_at": "..."}
 ],
 "server_time": "<ISO-vaqt>"}
```
`changes` ichidagi yozuvlar doim `deleted: false`; o'chirishlar alohida
yuqori darajadagi `deleted` massivida keladi (tombstones).

### POST /sync/push
```json
{"device_id": "<uuid>",
 "changes": [ ... ],          // yuqoridagi format
 "deleted": [{"table": ..., "uid": ..., "deleted_at": ...}]}
```
Javob:
```json
{"ok": true, "applied": 12, "skipped": 3, "deleted": 1, "conflicts": 1,
 "pending": [{"table": "group_members", "uid": "..."}],
 "server_time": "...", "last_change_at": "..."}
```
- `conflicts` — desktop tomoni yangiroq bo'lgan qatorlar soni
  (sensitiv ma'lumot yo'q, faqat son).
- **`pending`** — bu syncda qo'llanmagan qatorlar (ota yozuv hali kelmagan).
  Telefon **faqat** shu ro'yxatdagi yozuvlarni outbox'da qoldiradi,
  qolganlari (applied/skipped/conflicts) outbox'dan o'chiriladi.
  Bo'sh `pending: []` — navbat to'liq tozalandi degani.
- Tani o'qib bo'lmasa (10MB+ yoki JSON xato) server `400` qaytaradi —
  bu holatda telefon outbox'ni o'chirmaydi.

## Vaqt va konflikt (LWW) — kompyuter soati domeni

- Barcha `server_time` qiymatlari **kompyuter (desktop) soati**.
- Telefon `hello`/`changes`/`push` javoblaridagi `server_time` dan
  `offset = server_time - telefon_hozir` ni hisoblab, barcha yozuv
  vaqtini (`updated_at`, `deleted_at`) shu domenga ko'chiradi
  (`SyncManager.clockOffsetMs`), keyin saqlanadi. Telefon soati
  noto'g'ri tursa ham konflikt **bir xil soat** bo'yicha hukm qiladi —
  ma'lumotlar ajralib ketmaydi.
- **Kursor:** telefondagi `since` = `changes` javobidagi `server_time`
  (desktop tomonida `collect` dan **oldin** olinadi), telefon soati emas.
  Shu sabab kompyuter yozgan yangiliklar soatlar farqida ham tushib qolmaydi.
- Konflikt qoidasi: `updated_at` kechroq bo'lgani yutadi; `tombstone`
  ustuvor (o'chirilgan qator qayta tirilmaydi).

## Jadvallar va maydonlar
`students, monthly_payments, attendance, test_results, reminders,
groups, group_members` — har birida `updated_at` (ISO8601) bo'ladi.
O'chirishlar `tombstones` orqali keladi:
`{"table": ..., "row_id": ..., "deleted_at": ...}`

## Xatolar
- `401` — token yo'q/noto'g'ri (qayta juftlash kerak)
- `400` — format xato (`{"error": "..."}`)
