package uz.kursmanager.data

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/** Barcha jadvalar desktop wire-format bilan bir xil ustunlarga ega.
 *  Sana-vaqtlar TEXT (ISO), mantiqiy qiymatlar Boolean sifatida. */

@Entity(tableName = "courses", indices = [Index(value = ["uid"], unique = true)])
data class Course(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val name: String = "",
    val price: Double = 0.0,
    val active: Boolean = true,
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "students", indices = [Index(value = ["uid"], unique = true)])
data class Student(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val full_name: String = "",
    val phone: String = "",
    val courseId: Long? = null,
    val courseUid: String = "",
    val payment_status: String = "unpaid",
    val fee: Double = 0.0,
    val total_price: Double = 0.0,
    val paid_amount: Double = 0.0,
    val grade: String = "",
    val note: String = "",
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "groups", indices = [Index(value = ["uid"], unique = true)])
data class Group(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val name: String = "",
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "group_members", indices = [Index(value = ["uid"], unique = true)])
data class GroupMember(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val groupId: Long? = null,
    val groupUid: String = "",
    val studentId: Long? = null,
    val studentUid: String = "",
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "payments", indices = [Index(value = ["uid"], unique = true)])
data class Payment(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val studentId: Long? = null,
    val studentUid: String = "",
    val amount: Double = 0.0,
    val status: String = "paid",
    val payment_date: String = "",
    val note: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "monthly_payments", indices = [Index(value = ["uid"], unique = true)])
data class MonthlyPayment(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val studentId: Long? = null,
    val studentUid: String = "",
    val year: Int = 0,
    val month: Int = 0,
    val paid: Boolean = true,
    val amount: Double = 0.0,
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "attendance", indices = [Index(value = ["uid"], unique = true)])
data class Attendance(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val studentId: Long? = null,
    val studentUid: String = "",
    val att_date: String = "",
    val present: Boolean = true,
    val note: String = "",
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "test_results", indices = [Index(value = ["uid"], unique = true)])
data class TestResult(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val studentId: Long? = null,
    val studentUid: String = "",
    val topic: String = "",
    val total_questions: Int = 0,
    val correct_answers: Int = 0,
    val percentage: Double = 0.0,
    val result_date: String = "",
    val note: String = "",
    val created_at: String = "",
    val updated_at: String = ""
)

@Entity(tableName = "reminders", indices = [Index(value = ["uid"], unique = true)])
data class Reminder(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String = "",
    val title: String = "",
    val note: String = "",
    val remind_at: String = "",
    val is_done: Boolean = false,
    val notified: Boolean = false,
    val created_at: String = "",
    val updated_at: String = ""
)

/** O'chirish qaydlari (qayta "tirilmaslik" uchun). */
@Entity(tableName = "tombstones")
data class Tombstone(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val tableName: String = "",
    val rowUid: String = "",
    val deletedAt: String = ""
)

/** Serverga yuborilmagan mahalliy o'zgarishlar navbati (offline outbox). */
@Entity(tableName = "outbox")
data class OutboxItem(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val tableName: String = "",
    val uid: String = "",
    val deleted: Boolean = false,
    val payload: String = "",
    val createdAt: String = ""
)
