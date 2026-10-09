package uz.kursmanager.sync

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import uz.kursmanager.R
import uz.kursmanager.ui.MainActivity
import java.time.LocalDateTime

const val CH_ID = "kurs_reminders"

/** Eslatma vaqti kelganda aniq vaqtda uyg'onadi. */
class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val title = intent.getStringExtra("title") ?: return
        val note = intent.getStringExtra("note") ?: ""
        showNotif(ctx, 1000 + (System.currentTimeMillis() % 9000).toInt(),
            "🔔 Eslatma: $title", note.ifEmpty { "Vaqti keldi!" })
    }
}

fun ensureChannel(ctx: Context) {
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CH_ID) == null) {
        nm.createNotificationChannel(
            android.app.NotificationChannel(CH_ID, "Eslatmalar", NotificationManager.IMPORTANCE_HIGH)
        )
    }
}

fun showNotif(ctx: Context, id: Int, title: String, text: String) {
    ensureChannel(ctx)
    val open = PendingIntent.getActivity(
        ctx, 0, Intent(ctx, MainActivity::class.java),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
    val n = NotificationCompat.Builder(ctx, CH_ID)
        .setSmallIcon(R.drawable.ic_bell)
        .setContentTitle(title)
        .setContentText(text)
        .setStyle(NotificationCompat.BigTextStyle().bigText(text))
        .setContentIntent(open)
        .setAutoCancel(true)
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .build()
    (ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(id, n)
}

/** Kelajakdagi eslatma uchun aniq alarm qo'yadi. */
fun scheduleReminderAlarm(ctx: Context, uid: String, title: String, note: String, remindAtIso: String) {
    try {
        val at = LocalDateTime.parse(remindAtIso, TS_FMT)
        val millis = at.atZone(java.time.ZoneId.systemDefault()).toInstant().toEpochMilli()
        if (millis <= System.currentTimeMillis()) return
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pi = PendingIntent.getBroadcast(
            ctx, uid.hashCode(), Intent(ctx, AlarmReceiver::class.java).apply {
                putExtra("title", title); putExtra("note", note)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        try {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, millis, pi)
        } catch (e: SecurityException) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, millis, pi)
        }
    } catch (e: Exception) { /* format xato */ }
}

fun cancelReminderAlarm(ctx: Context, uid: String) {
    val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
    val pi = PendingIntent.getBroadcast(
        ctx, uid.hashCode(), Intent(ctx, AlarmReceiver::class.java),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
    am.cancel(pi)
}

