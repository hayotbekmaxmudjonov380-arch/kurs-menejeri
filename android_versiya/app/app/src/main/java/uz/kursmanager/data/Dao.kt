package uz.kursmanager.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update

@Dao
interface CourseDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Course): Long
    @Query("SELECT * FROM courses WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Course?
    @Query("SELECT * FROM courses ORDER BY name ASC") suspend fun all(): List<Course>
    @Query("SELECT * FROM courses WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Course>
    @Query("DELETE FROM courses WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface StudentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Student): Long
    @Query("SELECT * FROM students WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Student?
    @Query("SELECT * FROM students ORDER BY full_name ASC, id ASC") suspend fun all(): List<Student>
    @Query("SELECT * FROM students WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Student>
    @Query("SELECT COUNT(*) FROM students") suspend fun count(): Int
    @Query("SELECT COUNT(*) FROM students WHERE payment_status = :s") suspend fun countByStatus(s: String): Int
    @Query("DELETE FROM students WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface GroupDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Group): Long
    @Query("SELECT * FROM groups WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Group?
    @Query("SELECT * FROM groups ORDER BY name ASC") suspend fun all(): List<Group>
    @Query("SELECT * FROM groups WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Group>
    @Query("DELETE FROM groups WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface GroupMemberDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: GroupMember): Long
    @Query("SELECT * FROM group_members WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): GroupMember?
    @Query("SELECT * FROM group_members ORDER BY id ASC") suspend fun all(): List<GroupMember>
    @Query("SELECT * FROM group_members WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<GroupMember>
    @Query("DELETE FROM group_members WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface PaymentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Payment): Long
    @Query("SELECT * FROM payments WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Payment?
    @Query("SELECT * FROM payments ORDER BY payment_date DESC, id DESC LIMIT :lim") suspend fun recent(lim: Int): List<Payment>
    @Query("SELECT * FROM payments WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Payment>
    @Query("SELECT IFNULL(SUM(amount),0) FROM payments WHERE status='paid'") suspend fun revenue(): Double
    @Query("DELETE FROM payments WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface MonthlyPaymentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: MonthlyPayment): Long
    @Query("SELECT * FROM monthly_payments WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): MonthlyPayment?
    @Query("SELECT * FROM monthly_payments ORDER BY year DESC, month DESC") suspend fun all(): List<MonthlyPayment>
    @Query("SELECT * FROM monthly_payments WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<MonthlyPayment>
    @Query("DELETE FROM monthly_payments WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface AttendanceDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Attendance): Long
    @Query("SELECT * FROM attendance WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Attendance?
    @Query("SELECT * FROM attendance WHERE att_date >= :fromD AND att_date <= :toD ORDER BY att_date ASC") suspend fun range(fromD: String, toD: String): List<Attendance>
    @Query("SELECT * FROM attendance WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Attendance>
    @Query("SELECT * FROM attendance WHERE studentId = :sid AND att_date = :d LIMIT 1") suspend fun one(sid: Long, d: String): Attendance?
    @Query("DELETE FROM attendance WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface TestResultDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: TestResult): Long
    @Query("SELECT * FROM test_results WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): TestResult?
    @Query("SELECT * FROM test_results ORDER BY result_date DESC, id DESC") suspend fun all(): List<TestResult>
    @Query("SELECT * FROM test_results WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<TestResult>
    @Query("DELETE FROM test_results WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface ReminderDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(e: Reminder): Long
    @Query("SELECT * FROM reminders WHERE uid = :uid LIMIT 1") suspend fun byUid(uid: String): Reminder?
    @Query("SELECT * FROM reminders ORDER BY remind_at ASC") suspend fun all(): List<Reminder>
    @Query("SELECT * FROM reminders WHERE is_done = 0 ORDER BY remind_at ASC") suspend fun pending(): List<Reminder>
    @Query("SELECT * FROM reminders WHERE updated_at > :since ORDER BY updated_at ASC") suspend fun since(since: String): List<Reminder>
    @Query("DELETE FROM reminders WHERE uid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface TombstoneDao {
    @Insert suspend fun insert(e: Tombstone)
    @Query("SELECT * FROM tombstones WHERE rowUid = :uid LIMIT 1") suspend fun byUid(uid: String): Tombstone?
    @Query("DELETE FROM tombstones WHERE rowUid = :uid") suspend fun deleteByUid(uid: String)
}

@Dao
interface OutboxDao {
    @Insert suspend fun insert(e: OutboxItem)
    @Query("SELECT * FROM outbox ORDER BY id ASC") suspend fun all(): List<OutboxItem>
    @Query("DELETE FROM outbox WHERE id = :id") suspend fun delete(id: Long)
    @Query("DELETE FROM outbox") suspend fun clear()
}
