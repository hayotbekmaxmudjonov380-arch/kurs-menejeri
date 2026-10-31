package uz.kursmanager.ui

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.PageRange
import android.print.PrintAttributes
import android.print.PrintDocumentAdapter
import android.print.PrintDocumentInfo
import android.text.TextPaint
import android.text.TextUtils
import java.io.FileOutputStream
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/** Test natijalarini A4 jadval sifatida PDF ga chiqaradi (Android print tizimi). */
class TestsPrintAdapter(
    private val studentNames: List<String>,
    private val dates: List<LocalDate>,
    private val cells: List<List<Double?>>,
    private val periodLabel: String = ""
) : PrintDocumentAdapter() {

    override fun onLayout(
        oldAttributes: PrintAttributes?,
        newAttributes: PrintAttributes,
        cancellationSignal: CancellationSignal,
        callback: LayoutResultCallback,
        extras: android.os.Bundle?
    ) {
        if (cancellationSignal.isCanceled) {
            callback.onLayoutFailed(null)
            return
        }
        val info = PrintDocumentInfo.Builder("Test_natijalari.pdf")
            .setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT)
            .setPageCount(1)
            .build()
        callback.onLayoutFinished(info, true)
    }

    override fun onWrite(
        pages: Array<out PageRange>,
        destination: ParcelFileDescriptor,
        cancellationSignal: CancellationSignal,
        callback: WriteResultCallback
    ) {
        val pdf = PdfDocument()
        try {
            val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create() // A4 @72dpi
            val page = pdf.startPage(pageInfo)
            drawTable(page.canvas, 595f, 842f)
            pdf.finishPage(page)
            FileOutputStream(destination.fileDescriptor).use { pdf.writeTo(it) }
            callback.onWriteFinished(arrayOf(PageRange.ALL_PAGES))
        } catch (e: Exception) {
            callback.onWriteFailed(e.message)
        } finally {
            pdf.close()
        }
    }

    private fun drawTable(c: Canvas, pageW: Float, pageH: Float) {
        c.drawColor(Color.WHITE)
        val margin = 24f
        var y = margin

        val titlePaint = TextPaint().apply {
            textSize = 15f
            isFakeBoldText = true
            color = Color.BLACK
        }
        val subPaint = TextPaint().apply {
            textSize = 9f
            color = Color.rgb(70, 70, 70)
        }
        c.drawText("Test natijalari — Kurs Manager", margin, y + 15, titlePaint)
        y += 24
        val today = LocalDate.now().format(DateTimeFormatter.ofPattern("dd.MM.yyyy"))
        val period = if (periodLabel.isBlank()) "" else " • $periodLabel"
        c.drawText(
            "Sana: $today$period • ${studentNames.size} ta o'quvchi • ${dates.size} ta sana",
            margin, y + 10, subPaint
        )
        y += 18

        val legend = listOf(
            "A'lo 85+" to Color.rgb(34, 197, 94),
            "Yaxshi 70+" to Color.rgb(43, 127, 255),
            "Qoniqarli 55+" to Color.rgb(245, 168, 11),
            "Qoniqarsiz" to Color.rgb(240, 67, 90)
        )
        var lx = margin
        val legendPaint = TextPaint().apply { textSize = 8f }
        legend.forEach { (label, col) ->
            legendPaint.color = col
            val text = "• $label"
            c.drawText(text, lx, y + 9, legendPaint)
            lx += legendPaint.measureText("$text    ")
        }
        y += 18

        val nameW = 100f
        val avail = pageW - margin * 2 - nameW
        val colW = if (dates.isEmpty()) avail else maxOf(14f, avail / dates.size)
        val headerH = 32f
        val rowH = 18f

        val border = Paint().apply {
            style = Paint.Style.STROKE
            strokeWidth = 0.7f
            color = Color.rgb(130, 130, 130)
        }
        val headerBg = Paint().apply { color = Color.rgb(228, 234, 245) }
        val zebra = Paint().apply { color = Color.rgb(245, 247, 251) }
        val headerText = TextPaint().apply {
            textSize = 9f
            isFakeBoldText = true
            color = Color.BLACK
        }
        val datePaint = TextPaint().apply {
            textSize = 6.5f
            isFakeBoldText = true
            color = Color.BLACK
        }
        val weekPaint = TextPaint().apply {
            textSize = 6f
            color = Color.rgb(90, 90, 90)
        }
        val namePaint = TextPaint().apply {
            textSize = 8.5f
            color = Color.BLACK
        }
        val cellPaintBase = TextPaint().apply {
            textSize = 8.5f
            isFakeBoldText = true
            textAlign = Paint.Align.CENTER
        }
        val weekShort = arrayOf("Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya")

        val tableRight = margin + nameW + dates.size * colW
        c.drawRect(margin, y, margin + nameW, y + headerH, headerBg)
        c.drawText("O'quvchi", margin + 4, y + 20, headerText)
        dates.forEachIndexed { i, d ->
            val x = margin + nameW + i * colW
            c.drawRect(x, y, x + colW, y + headerH, headerBg)
            val shortDate = d.format(DateTimeFormatter.ofPattern("dd.MM"))
            c.drawText(shortDate, x + 2, y + 13, datePaint)
            c.drawText(weekShort[d.dayOfWeek.value - 1], x + 2, y + 24, weekPaint)
        }
        c.drawRect(margin, y, tableRight, y + headerH, border)
        dates.indices.forEach { i ->
            val x = margin + nameW + i * colW
            c.drawLine(x, y, x, y + headerH, border)
        }
        y += headerH

        studentNames.indices.forEach { ri ->
            val rowBottom = y + rowH
            if (ri % 2 == 1) {
                c.drawRect(margin, y, tableRight, rowBottom, zebra)
            }
            val name = TextUtils.ellipsize(studentNames[ri], namePaint, nameW - 8, TextUtils.TruncateAt.END).toString()
            c.drawText(name, margin + 4, y + 12.5f, namePaint)
            dates.indices.forEach { ci ->
                val x = margin + nameW + ci * colW
                val pct = cells.getOrNull(ri)?.getOrNull(ci)
                if (pct != null) {
                    val paint = TextPaint(cellPaintBase).apply { color = gradeColor(pct) }
                    c.drawText("${"%.0f".format(pct)}%", x + colW / 2, y + 12.5f, paint)
                }
            }
            c.drawRect(margin, y, tableRight, rowBottom, border)
            y = rowBottom
        }

        c.drawText("Kurs Manager • avtomatik hujjat", margin, pageH - margin, subPaint)
    }

    private fun gradeColor(pct: Double): Int = when {
        pct >= 85 -> Color.rgb(34, 197, 94)
        pct >= 70 -> Color.rgb(43, 127, 255)
        pct >= 55 -> Color.rgb(245, 168, 11)
        else -> Color.rgb(240, 67, 90)
    }
}
