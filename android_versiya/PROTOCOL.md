# Sync protokoli v1 (HTTP + JSON, 8741-port)

Barcha so'rovlar sarlavhada token yuboradi (juftlashdan keyingilari):
```
X-Device-Token: <32-bayt-hex>
```

## Juftlash (tokensiz)

### POST /sync/hello
Kompyuterni topish. Javob:
```json
{"app": "KursManager", "version": "1.3.5", "needs_pairing": true}
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
Shu vaqtdan keyingi o'zgarishlar:
```json
{"changes": [
  {"table": "students", "row": {...}, "updated_at": "...", "deleted": false},
  {"table": "students", "row": {"id": 7}, "updated_at": "...", "deleted": true}
]}
```

### POST /sync/push
```json
{"device_id": "<uuid>", "changes": [ ... ]}  // yuqoridagi format
```
Javob:
```json
{"applied": 12, "conflicts": 1}
```
`conflicts` — desktop tomoni yangiroq bo'lgan qatorlar soni
(sensitiv ma'lumot yo'q, faqat son).

## Jadvallar va maydonlar
`students, monthly_payments, attendance, test_results, reminders,
groups, group_members` — har birida `updated_at` (ISO8601) bo'ladi.
O'chirishlar `tombstones` orqali keladi:
`{"table": ..., "row_id": ..., "deleted_at": ...}`

## Xatolar
- `401` — token yo'q/noto'g'ri (qayta juftlash kerak)
- `400` — format xato (`{"error": "..."}`)
