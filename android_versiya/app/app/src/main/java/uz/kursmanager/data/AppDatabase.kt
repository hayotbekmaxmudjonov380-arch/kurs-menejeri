package uz.kursmanager.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        Course::class, Student::class, Group::class, GroupMember::class,
        Payment::class, MonthlyPayment::class, Attendance::class,
        TestResult::class, Reminder::class, Tombstone::class, OutboxItem::class
    ],
    version = AppDatabase.DB_VERSION,
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
        /**
         * Baza tuzilishi versiyasi.
         * Entity o'zgarsa: shu raqamni oshir + shu pastdagi MIGRATIONS ga
         * yangi Migration(ESKI, YANGI) qo'sh. fallback destructive YO'Q —
         * ma'lumot o'chmasligi shart.
         */
        const val DB_VERSION = 1

        /**
         * Migratsiyalar tartib bilan: (1→2), (2→3), ...
         * Har biri avvalgisiga tayanadi, shuning uchun ketma-ket qo'shiladi.
         *
         * Namuna (ustun qo'shish uchun):
         * object : Migration(1, 2) {
         *     override fun migrate(db: SupportSQLiteDatabase) {
         *         db.execSQL(
         *             "ALTER TABLE students ADD COLUMN note2 TEXT NOT NULL DEFAULT ''"
         *         )
         *     }
         * }
         */
        private val MIGRATIONS: Array<Migration> = arrayOf(
            // yer: Migration(1, 2), Migration(2, 3), ...
        )

        @Volatile private var I: AppDatabase? = null

        fun get(ctx: Context): AppDatabase =
            I ?: synchronized(this) {
                I ?: Room.databaseBuilder(
                    ctx.applicationContext,
                    AppDatabase::class.java,
                    "kurs_manager.db"
                )
                    .addMigrations(*MIGRATIONS)
                    .build()
                    .also { I = it }
            }
    }
}
