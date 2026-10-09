package uz.kursmanager.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        Course::class, Student::class, Group::class, GroupMember::class,
        Payment::class, MonthlyPayment::class, Attendance::class,
        TestResult::class, Reminder::class, Tombstone::class, OutboxItem::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun courses(): CourseDao
    abstract fun students(): StudentDao
    abstract fun groups(): GroupDao
    abstract fun groupMembers(): GroupMemberDao
    abstract fun payments(): PaymentDao
    abstract fun monthlyPayments(): MonthlyPaymentDao
    abstract fun attendance(): AttendanceDao
    abstract fun testResults(): TestResultDao
    abstract fun reminders(): ReminderDao
    abstract fun tombstones(): TombstoneDao
    abstract fun outbox(): OutboxDao

    companion object {
        @Volatile private var I: AppDatabase? = null
        fun get(ctx: Context): AppDatabase =
            I ?: synchronized(this) {
                I ?: Room.databaseBuilder(ctx.applicationContext, AppDatabase::class.java, "kurs_manager.db")
                    .fallbackToDestructiveMigration()
                    .build().also { I = it }
            }
    }
}
