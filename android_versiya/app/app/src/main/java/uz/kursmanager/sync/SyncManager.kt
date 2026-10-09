package uz.kursmanager.sync

import android.content.Context
import android.content.SharedPreferences
import android.provider.Settings
import uz.kursmanager.data.AppDatabase
import uz.kursmanager.data.Attendance
import uz.kursmanager.data.Course
import uz.kursmanager.data.Group
import uz.kursmanager.data.GroupMember
import uz.kursmanager.data.MonthlyPayment
import uz.kursmanager.data.OutboxItem
import uz.kursmanager.data.Payment
import uz.kursmanager.data.Reminder
import uz.kursmanager.data.Student
import uz.kursmanager.data.TestResult
import uz.kursmanager.data.Tombstone
import uz.kursmanager.net.ApiFactory
import uz.kursmanager.net.ChangeItem
import uz.kursmanager.net.PairReq
import uz.kursmanager.net.PushReq
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

private const val PREFS = "kurs_sync"
private const val K_URL = "server_url"
private const val K_TOKEN = "token"
private const val K_DEVICE = "device_id"
private const val K_LAST = "last_sync_at"
private const val DEF_URL = "http://10.0.2.2:8741"

val TS_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS")

fun nowIso(): String = LocalDateTime.now().format(TS_FMT)
fun newUid(): String = UUID.randomUUID().toString().replace("-", "")

fun num(m: Map<String, Any?>, k: String, d: Double = 0.0): Double =
    (m[k] as? Number)?.toDouble() ?: (m[k]?.toString()?.toDoubleOrNull() ?: d)

fun intNum(m: Map<String, Any?>, k: String, d: Int = 0): Int =
    (m[k] as? Number)?.toInt() ?: (m[k]?.toString()?.toIntOrNull() ?: d)

fun str(m: Map<String, Any?>, k: String): String = m[k]?.toString() ?: ""
fun bool(m: Map<String, Any?>, k: String): Boolean =
    when (val v = m[k]) {
        is Boolean -> v
        is Number -> v.toInt() != 0
        is String -> v == "1" || v.equals("true", true)
        else -> false
    }

class SyncManager(ctx: Context) {
    private val app = ctx.applicationContext
    private val db = uz.kursmanager.data.AppDatabase.get(app)
    private val prefs: SharedPreferences = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(K_URL, DEF_URL) ?: DEF_URL
        set(v) = prefs.edit().putString(K_URL, v.trim().trimEnd('/')).apply()
    var token: String
        get() = prefs.getString(K_TOKEN, "") ?: ""
        set(v) = prefs.edit().putString(K_TOKEN, v).apply()
    val deviceId: String
        get() {
            var id = prefs.getString(K_DEVICE, "")
            if (id.isNullOrEmpty()) {
                id = Settings.Secure.getString(app.contentResolver, Settings.Secure.ANDROID_ID)
                    ?: UUID.randomUUID().toString()
                prefs.edit().putString(K_DEVICE, id).apply()
            }
            return id!!
        }
    var lastSyncAt: String
        get() = prefs.getString(K_LAST, "") ?: ""
        set(v) = prefs.edit().putString(K_LAST, v).apply()

    val isPaired: Boolean get() = token.isNotEmpty()
    private fun api() = ApiFactory.create(serverUrl)

    // ---------- Juftlash ----------

    suspend fun hello(): Result<String> = runCatching {
        val h = api().hello()
        if (h.app != "KursManager") throw IllegalStateException("Bu KursManager serveri emas")
        h.version
    }

    suspend fun pair(code: String, deviceName: String): Result<String> = runCatching {
        val r = api().pair(PairReq(deviceId, deviceName, code.trim()))
        if (!r.ok || r.token.isEmpty()) throw IllegalStateException(r.error.ifEmpty { "Kod noto'g'ri" })
        token = r.token
        r.token
    }

    fun unpair() {
        token = ""
        lastSyncAt = ""
    }

    // ---------- To'liq sinxron ----------

    data class SyncResult(val pulled: Int, val pushed: Int, val conflicts: Int)

    suspend fun fullSync(): Result<SyncResult> = runCatching {
        if (!isPaired) throw IllegalStateException("Avval kompyuterga ulaning")
        var pulled = 0
        // 1) pastga: server o'zgarishlarini olamiz
        val resp = api().changes(token, lastSyncAt, deviceId)
        for (t in resp.deleted) applyTomb(
            t["table"]?.toString() ?: "", t["uid"]?.toString() ?: ""
        )
        for (c in resp.changes) {
            if (c.deleted) applyTomb(c.table, c.uid) else if (applyOne(c)) pulled++
        }
        // 2) yuqoriga: navbatdagilarni yuboramiz
        val outbox = db.outbox().all()
        var pushed = 0
        var conflicts = 0
        if (outbox.isNotEmpty()) {
            val ups = outbox.filter { !it.deleted }
            val dels = outbox.filter { it.deleted }
            val items = ups.map {
                ChangeItem(it.tableName, it.uid, nowIso(), false,
                    com.google.gson.Gson().fromJson(it.payload, Map::class.java) as Map<String, Any?>)
            }
            val delItems = dels.map {
                mapOf("table" to it.tableName, "uid" to it.uid, "deleted_at" to nowIso())
            }
            val pr = api().push(token, PushReq(deviceId, items, delItems))
            pushed = pr.applied
            conflicts = pr.conflicts
            // skipped == 0 bo'lsagina navbat tozalanadi, aks holda
            // keyingi sinxronga qoladi (ma'lumot yo'qolmaydi)
            if (pr.skipped == 0) {
                for (o in outbox) db.outbox().delete(o.id)
            }
        }
        lastSyncAt = nowIso()
        SyncResult(pulled, pushed, conflicts)
    }

    // ---------- Merge (UID + updated_at, kechroq yutadi) ----------

    private suspend fun isTombstoned(uid: String): Boolean =
        uid.isNotEmpty() && db.tombstones().byUid(uid) != null

    private suspend fun applyTomb(table: String, uid: String) {
        if (table.isEmpty() || uid.isEmpty()) return
        deleteLocal(table, uid)
        if (db.tombstones().byUid(uid) == null)
            db.tombstones().insert(Tombstone(tableName = table, rowUid = uid, deletedAt = nowIso()))
    }

    private fun newerThan(incoming: String, local: String): Boolean =
        incoming.isNotEmpty() && (local.isEmpty() || incoming > local)

    private suspend fun applyOne(c: ChangeItem): Boolean {
        val table = c.table
        val row = c.row
        val uid = c.uid.ifEmpty { str(row, "uid") }
        if (table.isEmpty() || uid.isEmpty()) return false
        if (isTombstoned(uid)) return false // biz o'chirganmiz - qayta "tirilmaydi"
        return when (table) {
            "courses" -> {
                val cur = db.courses().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                db.courses().upsert(Course(
                    id = cur?.id ?: 0, uid = uid,
                    name = str(row, "name"), price = num(row, "price"),
                    active = bool(row, "active").let { if (row.containsKey("active")) it else true },
                    created_at = str(row, "created_at"),
                    updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "students" -> {
                val cur = db.students().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val courseUid = str(row, "course_id_uid")
                val courseId = if (courseUid.isEmpty()) null else db.courses().byUid(courseUid)?.id
                db.students().upsert(Student(
                    id = cur?.id ?: 0, uid = uid,
                    full_name = str(row, "full_name"), phone = str(row, "phone"),
                    courseId = courseId, courseUid = courseUid,
                    payment_status = str(row, "payment_status").ifEmpty { "unpaid" },
                    fee = num(row, "fee"), total_price = num(row, "total_price"),
                    paid_amount = num(row, "paid_amount"), grade = str(row, "grade"),
                    note = str(row, "note"), created_at = str(row, "created_at"),
                    updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "groups" -> {
                val cur = db.groups().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                db.groups().upsert(Group(
                    id = cur?.id ?: 0, uid = uid, name = str(row, "name"),
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "group_members" -> {
                val cur = db.groupMembers().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val gUid = str(row, "group_id_uid"); val sUid = str(row, "student_id_uid")
                val gId = if (gUid.isEmpty()) null else db.groups().byUid(gUid)?.id
                val sId = if (sUid.isEmpty()) null else db.students().byUid(sUid)?.id
                if ((gUid.isNotEmpty() && gId == null) || (sUid.isNotEmpty() && sId == null)) return false
                db.groupMembers().upsert(GroupMember(
                    id = cur?.id ?: 0, uid = uid, groupId = gId, groupUid = gUid,
                    studentId = sId, studentUid = sUid,
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "payments" -> {
                val cur = db.payments().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val sUid = str(row, "student_id_uid")
                val sId = if (sUid.isEmpty()) null else db.students().byUid(sUid)?.id
                if (sUid.isNotEmpty() && sId == null) return false
                db.payments().upsert(Payment(
                    id = cur?.id ?: 0, uid = uid, studentId = sId, studentUid = sUid,
                    amount = num(row, "amount"), status = str(row, "status").ifEmpty { "paid" },
                    payment_date = str(row, "payment_date"), note = str(row, "note"),
                    updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "monthly_payments" -> {
                val cur = db.monthlyPayments().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val sUid = str(row, "student_id_uid")
                val sId = if (sUid.isEmpty()) null else db.students().byUid(sUid)?.id
                if (sUid.isNotEmpty() && sId == null) return false
                db.monthlyPayments().upsert(MonthlyPayment(
                    id = cur?.id ?: 0, uid = uid, studentId = sId, studentUid = sUid,
                    year = intNum(row, "year"), month = intNum(row, "month"),
                    paid = bool(row, "paid").let { if (row.containsKey("paid")) it else true },
                    amount = num(row, "amount"),
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "attendance" -> {
                val cur = db.attendance().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val sUid = str(row, "student_id_uid")
                val sId = if (sUid.isEmpty()) null else db.students().byUid(sUid)?.id
                if (sUid.isNotEmpty() && sId == null) return false
                db.attendance().upsert(Attendance(
                    id = cur?.id ?: 0, uid = uid, studentId = sId, studentUid = sUid,
                    att_date = str(row, "att_date"),
                    present = bool(row, "present").let { if (row.containsKey("present")) it else true },
                    note = str(row, "note"),
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "test_results" -> {
                val cur = db.testResults().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                val sUid = str(row, "student_id_uid")
                val sId = if (sUid.isEmpty()) null else db.students().byUid(sUid)?.id
                if (sUid.isNotEmpty() && sId == null) return false
                db.testResults().upsert(TestResult(
                    id = cur?.id ?: 0, uid = uid, studentId = sId, studentUid = sUid,
                    topic = str(row, "topic"),
                    total_questions = intNum(row, "total_questions"),
                    correct_answers = intNum(row, "correct_answers"),
                    percentage = num(row, "percentage"),
                    result_date = str(row, "result_date"), note = str(row, "note"),
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            "reminders" -> {
                val cur = db.reminders().byUid(uid)
                val upd = str(row, "updated_at")
                if (cur != null && !newerThan(upd, cur.updated_at)) return false
                db.reminders().upsert(Reminder(
                    id = cur?.id ?: 0, uid = uid, title = str(row, "title"),
                    note = str(row, "note"), remind_at = str(row, "remind_at"),
                    is_done = bool(row, "is_done"), notified = bool(row, "notified"),
                    created_at = str(row, "created_at"), updated_at = upd.ifEmpty { nowIso() }
                )); true
            }
            else -> false
        }
    }

    private suspend fun deleteLocal(table: String, uid: String) {
        when (table) {
            "courses" -> db.courses().deleteByUid(uid)
            "students" -> db.students().deleteByUid(uid)
            "groups" -> db.groups().deleteByUid(uid)
            "group_members" -> db.groupMembers().deleteByUid(uid)
            "payments" -> db.payments().deleteByUid(uid)
            "monthly_payments" -> db.monthlyPayments().deleteByUid(uid)
            "attendance" -> db.attendance().deleteByUid(uid)
            "test_results" -> db.testResults().deleteByUid(uid)
            "reminders" -> db.reminders().deleteByUid(uid)
        }
    }

    // ---------- Mahalliy yozuv -> outbox ----------

    suspend fun enqueue(table: String, uid: String, deleted: Boolean, payloadJson: String) {
        db.outbox().insert(OutboxItem(tableName = table, uid = uid, deleted = deleted, payload = payloadJson, createdAt = nowIso()))
    }

    suspend fun markDeleted(table: String, uid: String) {
        deleteLocal(table, uid)
        db.tombstones().insert(Tombstone(tableName = table, rowUid = uid, deletedAt = nowIso()))
        enqueue(table, uid, true, "{}")
    }
}
