package uz.kursmanager.ui

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.view.Gravity
import android.widget.TextView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import uz.kursmanager.R

fun statusBadge(ctx: Context, text: String, colorHex: String): TextView {
    val c = Color.parseColor(colorHex)
    val d = ctx.resources.displayMetrics.density
    val fill = (c and 0x00FFFFFF) or (0x2E shl 24)          // ~18% shaffof fon
    val strokeCol = (c and 0x00FFFFFF) or (0x99 shl 24)      // ~60% ramka
    return TextView(ctx).apply {
        this.text = text
        setTextColor(c)
        setTypeface(typeface, Typeface.BOLD)
        textSize = 11.5f
        gravity = Gravity.CENTER
        setPadding((10 * d).toInt(), (4 * d).toInt(), (10 * d).toInt(), (4 * d).toInt())
        background = android.graphics.drawable.GradientDrawable().apply {
            shape = android.graphics.drawable.GradientDrawable.RECTANGLE
            cornerRadius = 20f * d
            setColor(fill)
            setStroke((1f * d).toInt().coerceAtLeast(1), strokeCol)
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
