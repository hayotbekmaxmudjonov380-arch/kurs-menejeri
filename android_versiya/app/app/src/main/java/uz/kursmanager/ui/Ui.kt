package uz.kursmanager.ui

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.view.Gravity
import android.widget.TextView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import uz.kursmanager.R

fun statusBadge(ctx: Context, text: String, colorHex: String): TextView {
    return TextView(ctx).apply {
        this.text = text
        setTextColor(Color.parseColor(colorHex))
        setTypeface(typeface, Typeface.BOLD)
        textSize = 12f
        gravity = Gravity.CENTER
        val pad = (10 * resources.displayMetrics.density).toInt()
        setPadding(pad, (5 * resources.displayMetrics.density).toInt(), pad, (5 * resources.displayMetrics.density).toInt())
        background = android.graphics.drawable.GradientDrawable().apply {
            shape = android.graphics.drawable.GradientDrawable.RECTANGLE
            cornerRadius = 24f
            setStroke(2, Color.parseColor(colorHex))
            alpha = 255
        }
    }
}

fun payStatusMeta(status: String): Pair<String, String> = when (status) {
    "paid" -> "● To'lov qilingan" to "#22C55E"
    "pending" -> "● Kutilmoqda" to "#F5A80B"
    else -> "● To'lov qilinmagan" to "#F0435A"
}

fun gradeMeta(pct: Double): Triple<String, String, String> = when {
    pct >= 85 -> Triple("A'lo", "#22C55E", "85+")
    pct >= 70 -> Triple("Yaxshi", "#2B7FFF", "70+")
    pct >= 55 -> Triple("Qoniqarli", "#F5A80B", "55+")
    else -> Triple("Qoniqarsiz", "#F0435A", "0+")
}

fun confirm(ctx: Context, msg: String, onYes: () -> Unit) {
    MaterialAlertDialogBuilder(ctx)
        .setTitle("Tasdiqlash")
        .setMessage(msg)
        .setPositiveButton("Ha") { _, _ -> onYes() }
        .setNegativeButton("Bekor qilish", null)
        .show()
}

fun initialsOf(name: String): String {
    val p = name.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
    return when {
        p.size >= 2 -> "${p[0][0]}${p[1][0]}".uppercase()
        p.size == 1 && p[0].length >= 2 -> p[0].take(2).uppercase()
        else -> "?"
    }
}
