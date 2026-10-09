package uz.kursmanager.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import uz.kursmanager.app
import java.time.LocalDate
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val a = applicationContext.app()
        if (a.sync.isPaired) {
            try { a.sync.fullSync() } catch (_: Exception) { /* offline — keyingi urinishda qayta */ }
        }
        try { checkDues() } catch (_: Exception) { /* notif xatosi workerni yiqitmasin */ }
        return Result.success()
    }

    /** Muddati yaqin/kechikkan to'lovlar uchun eslatma. */
    private suspend fun checkDues() {
        val a = applicationContext.app()
        val prefs = applicationContext.getSharedPreferences("kurs_sync", Context.MODE_PRIVATE)
        val today = LocalDate.now()
        for (st in a.repo.students()) {
            val parsed = runCatching {
                LocalDateTime.parse(st.created_at, TS_FMT).toLocalDate()
            }.getOrNull() ?: continue
            val created: LocalDate = parsed
            var k = 1
            var due = created.plusMonths(k.toLong()).minusDays(1)
            while (!due.isAfter(today) && k < 1200) { k++; due = created.plusMonths(k.toLong()).minusDays(1) }
            val days = java.time.temporal.ChronoUnit.DAYS.between(today, due).toInt()
            val fire = when {
                st.payment_status != "paid" && days <= 0 -> "over"
                days in 1..3 -> days.toString()
                else -> null
            } ?: continue
            val key = "paydue_${st.uid}_${due}_$fire"
            if (prefs.getBoolean(key, false)) continue
            prefs.edit().putBoolean(key, true).apply()
            val text = if (fire == "over") "${st.full_name}: to'lov kechikkan ($due)"
                       else "${st.full_name}: $days kundan keyin ($due)"
            showNotif(applicationContext, 2000 + (st.id % 9000).toInt(), "💳 To'lov eslatmasi", text)
        }
    }

    companion object {
        private const val WORK_NAME = "kurs_auto_sync"

        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request
            )
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
