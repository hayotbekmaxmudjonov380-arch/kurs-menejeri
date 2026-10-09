package uz.kursmanager.data

import com.google.gson.Gson
import uz.kursmanager.sync.bool
import uz.kursmanager.sync.newUid
import uz.kursmanager.sync.nowIso
import uz.kursmanager.sync.num
import uz.kursmanager.sync.str
import uz.kursmanager.sync.SyncManager

/** Barcha yozishlar: uid + updated_at + outbox (serverga yuborish uchun). */
class Repo(private val db: AppDatabase, private val sync: SyncManager) {
    private val gson = Gson()

    // ---------- Courses ----------
    suspend fun courses(): List<Course> = db.courses().all()

    // ---------- Students ----------
    suspend fun students(): List<Student> = db.students().all()
    suspend fun studentCount(): Int = db.students().count()
    suspend fun countByStatus(s: String): Int = db.students().countByStatus(s)

    suspend fun addStudent(fullName: String, phone: String, courseUid: String, status: String,
                           fee: Double, note: String, grade: String = "", createdAt: String = nowIso()): Long {
        val course = courseUid.takeIf { it.isNotBlank() }?.let { db.courses().byUid(it) }
        val e = Student(uid = newUid(), full_name = fullName.trim(), phone = phone.trim(),
            courseId = course?.id, courseUid = course?.uid ?: "", payment_status = status,
            fee = fee, grade = grade, note = note.trim(), created_at = createdAt, updated_at = nowIso())
        val id = db.students().upsert(e)
        enqueueStudent(e.copy(id = id))
        return id
    }

    suspend fun updateStudent(e: Student) {
        val upd = e.copy(updated_at = nowIso())
        db.students().upsert(upd)
        enqueueStudent(upd)
    }

    suspend fun setPaymentStatus(uid: String, status: String) {
        val cur = db.students().byUid(uid) ?: return
        val upd = cur.copy(payment_status = status, updated_at = nowIso())
        db.students().upsert(upd)
        enqueueStudent(upd)
    }

    suspend fun deleteStudent(uid: String) = sync.markDeleted("students", uid)

    private suspend fun enqueueStudent(e: Student) {
        sync.enqueue("students", e.uid, false, gson.toJson(mapOf(
            "uid" to e.uid, "full_name" to e.full_name, "phone" to e.phone,
            "course_id_uid" to e.courseUid, "payment_status" to e.payment_status,
            "fee" to e.fee, "total_price" to e.total_price, "paid_amount" to e.paid_amount,
            "grade" to e.grade, "note" to e.note, "created_at" to e.created_at,
            "updated_at" to e.updated_at
        )))
    }

    // ---------- Payments ----------
    suspend fun recentPayments(): List<Payment> = db.payments().recent(200)
    suspend fun revenue(): Double = db.payments().revenue()

    suspend fun addPayment(studentUid: String, amount: Double, status: String, dateIso: String, note: String) {
        val st = db.students().byUid(studentUid)
        val e = Payment(uid = newUid(), studentId = st?.id, studentUid = studentUid,
            amount = amount, status = status, payment_date = dateIso,
            note = note.trim(), updated_at = nowIso())
        val id = db.payments().upsert(e)
        sync.enqueue("payments", e.uid, false, gson.toJson(mapOf(
            "uid" to e.uid, "student_id_uid" to studentUid, "amount" to amount,
            "status" to status, "payment_date" to dateIso, "note" to e.note,
            "updated_at" to e.updated_at
        )))
    }

    suspend fun deletePayment(uid: String) = sync.markDeleted("payments", uid)

    // ---------- Test results ----------
    suspend fun testResults(): List<TestResult> = db.testResults().all()

    suspend fun addTestResult(studentUid: String, topic: String, total: Int, correct: Int, dateIso: String, note: String) {
        val st = db.students().byUid(studentUid)
        val pct = if (total > 0) Math.round(correct * 1000.0 / total) / 10.0 else 0.0
        val e = TestResult(uid = newUid(), studentId = st?.id, studentUid = studentUid,
            topic = topic.trim(), total_questions = total, correct_answers = correct,
            percentage = pct, result_date = dateIso, note = note.trim(), updated_at = nowIso())
        db.testResults().upsert(e)
        sync.enqueue("test_results", e.uid, false, gson.toJson(mapOf(
            "uid" to e.uid, "student_id_uid" to studentUid, "topic" to e.topic,
            "total_questions" to total, "correct_answers" to correct, "percentage" to pct,
            "result_date" to dateIso, "note" to e.note, "updated_at" to e.updated_at
        )))
    }

    suspend fun deleteTestResult(uid: String) = sync.markDeleted("test_results", uid)

    // ---------- Attendance ----------
    suspend fun attendanceRange(fromD: String, toD: String): List<Attendance> = db.attendance().range(fromD, toD)
    suspend fun attendanceOne(sid: Long, d: String): Attendance? = db.attendance().one(sid, d)

    suspend fun setAttendance(studentUid: String, dateIso: String, present: Boolean?) {
        val st = db.students().byUid(studentUid) ?: return
        val cur = db.attendance().one(st.id, dateIso)
        if (present == null) {
            if (cur != null) sync.markDeleted("attendance", cur.uid)
            return
        }
        val e = (cur?.copy(present = present, updated_at = nowIso()))
            ?: Attendance(uid = newUid(), studentId = st.id, studentUid = studentUid,
                att_date = dateIso, present = present, updated_at = nowIso())
        db.attendance().upsert(e)
        sync.enqueue("attendance", e.uid, false, gson.toJson(mapOf(
            "uid" to e.uid, "student_id_uid" to studentUid, "att_date" to dateIso,
            "present" to present, "note" to e.note, "updated_at" to e.updated_at
        )))
    }

    // ---------- Reminders ----------
    suspend fun reminders(): List<Reminder> = db.reminders().all()
    suspend fun pendingReminders(): List<Reminder> = db.reminders().pending()

    suspend fun addReminder(title: String, note: String, remindAtIso: String) {
        val e = Reminder(uid = newUid(), title = title.trim(), note = note.trim(),
            remind_at = remindAtIso, updated_at = nowIso())
        db.reminders().upsert(e)
        sync.enqueue("reminders", e.uid, false, gson.toJson(mapOf(
            "uid" to e.uid, "title" to e.title, "note" to e.note,
            "remind_at" to remindAtIso, "is_done" to false, "notified" to false,
            "updated_at" to e.updated_at
        )))
    }

    suspend fun setReminderDone(uid: String, done: Boolean) {
        val cur = db.reminders().byUid(uid) ?: return
        val upd = cur.copy(is_done = done, updated_at = nowIso())
        db.reminders().upsert(upd)
        sync.enqueue("reminders", uid, false, gson.toJson(mapOf(
            "uid" to uid, "title" to upd.title, "note" to upd.note,
            "remind_at" to upd.remind_at, "is_done" to done, "notified" to upd.notified,
            "updated_at" to upd.updated_at
        )))
    }

    suspend fun deleteReminder(uid: String) = sync.markDeleted("reminders", uid)
}
