package uz.kursmanager.ui

import android.app.DatePickerDialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.data.Student
import uz.kursmanager.data.TestResult
import uz.kursmanager.databinding.DialogTestBinding
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter

/**
 * Test natijalari — oy filtri bilan jadval:
 * yuqorida to'liq sanalar, chapda o'quvchilar, katakchalar kvadratcha
 * (foiz kiritish/o'chirish).
 */
class TestsFragment : Fragment() {

    private lateinit var namesCol: LinearLayout
    private lateinit var gridCol: LinearLayout
    private lateinit var emptyState: TextView
    private lateinit var tvMeta: TextView
    private lateinit var btnMonth: TextView
    private lateinit var legendRow: LinearLayout
    private lateinit var tableScroll: ScrollView

    private var studentsAll: List<Student> = emptyList()
    private var testsAll: List<TestResult> = emptyList()
    private var curStudents: List<Student> = emptyList()
    private var curColumns: List<LocalDate> = emptyList()

    /** null = barcha sanalar (filtrsiz). */
    private var selectedMonth: YearMonth? = YearMonth.now()

    private val dateFmt = DateTimeFormatter.ofPattern("dd.MM.yyyy")
    private val monthNames = arrayOf(
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktyabr", "Noyabr", "Dekabr"
    )
    private val weekShort = arrayOf("Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya")

    private var namesW: Int = 0
    private var colW: Int = 0
    private var cellH: Int = 0
    private var headH: Int = 0
    private var searchBox: EditText? = null

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_tests, c, false)
        namesCol = v.findViewById(R.id.namesCol)
        gridCol = v.findViewById(R.id.gridCol)
        emptyState = v.findViewById(R.id.emptyState)
        tvMeta = v.findViewById(R.id.tvMeta)
        btnMonth = v.findViewById(R.id.btnMonth)
        legendRow = v.findViewById(R.id.legendRow)
        tableScroll = v.findViewById(R.id.tableScroll)

        cellH = dp(58)
        headH = dp(46)
        // Chapdagi o'quvchilar ustuni — ekranga mos (30%, chegaralar bilan)
        val scrW = resources.displayMetrics.widthPixels
        namesW = (scrW * 0.30f).toInt().coerceIn(dp(104), dp(146))
        (namesCol.layoutParams as LinearLayout.LayoutParams).width = namesW
        // Katakcha kengligi ham ekranga moslanadi: kichik telefonda ham
        // ~4 ta test ustuni ko'rinib turadi, katta ekranda katak kattalashadi.
        val availW = (scrW - namesW)
        colW = (availW / 4).coerceIn(dp(48), dp(76))

        buildLegend()
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showForm(null, null, null) }
        v.findViewById<ImageButton>(R.id.btnPrint).setOnClickListener { printPdf() }
        btnMonth.setOnClickListener { showMonthMenu() }
        v.findViewById<EditText>(R.id.inSearch).apply {
            hint = "O'quvchi qidirish..."
            searchBox = this
            addTextChangedListener(SimpleWatcher { reload(it) })
        }
        reload()
        return v
    }

    // ---------- Oy filtri ----------

    private fun monthLabel(m: YearMonth): String =
        "${monthNames[m.monthValue - 1]} ${m.year}"

    private fun showMonthMenu() {
        val pm = PopupMenu(requireContext(), btnMonth)
        val months = availableMonths()
        pm.menu.add(0, 0, 0, "📅 Barcha sanalar")
        months.forEachIndexed { i, m -> pm.menu.add(0, i + 1, i + 1, "📅 ${monthLabel(m)}") }
        pm.setOnMenuItemClickListener { item ->
            selectedMonth = if (item.itemId == 0) null else months[item.itemId - 1]
            reload()
            true
        }
        pm.show()
    }

    private fun availableMonths(): List<YearMonth> {
        val now = YearMonth.now()
        val fromData = testsAll.mapNotNull { parseDate(it.result_date)?.yearMonth }
        val calendarMonths = listOf(now.year - 1, now.year, now.year + 1).flatMap { y ->
            (1..12).map { YearMonth.of(y, it) }
        }
        return (fromData + calendarMonths).distinct().sortedDescending()
    }

    private fun updateMonthButton() {
        btnMonth.text = selectedMonth?.let { "📅 ${monthLabel(it)} ▾" } ?: "📅 Barcha sanalar ▾"
    }

    // ---------- Ma'lumot ----------

    private fun buildLegend() {
        legendRow.removeAllViews()
        listOf(
            "A'lo 85+" to "#22C55E",
            "Yaxshi 70+" to "#2B7FFF",
            "Qoniqarli 55+" to "#F5A80B",
            "Qoniqarsiz" to "#F0435A"
        ).forEach { (label, hex) ->
            val item = LinearLayout(requireContext()).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                val lp = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { marginEnd = dp(12) }
                layoutParams = lp
            }
            val dot = View(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(dp(7), dp(7))
                background = android.graphics.drawable.GradientDrawable().apply {
                    shape = android.graphics.drawable.GradientDrawable.OVAL
                    setColor(Color.parseColor(hex))
                }
            }
            val tv = TextView(requireContext()).apply {
                text = label
                textSize = 11f
                setTextColor(ContextCompat.getColor(context, R.color.text_dim))
                setPadding(dp(5), 0, 0, 0)
            }
            item.addView(dot)
            item.addView(tv)
            legendRow.addView(item)
        }
    }

    /** filter = null bo'lsa qidiruv maydonidagi matn saqlanadi. */
    private fun reload(filter: String? = null) {
        val q0 = (filter ?: searchBox?.text?.toString() ?: "").trim().lowercase()
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            studentsAll = repo.students().sortedBy { it.full_name.lowercase() }
            testsAll = repo.testResults()
            val q = q0
            curStudents = studentsAll.filter { q.isEmpty() || it.full_name.lowercase().contains(q) }

            val month = selectedMonth
            curColumns = if (month != null) {
                (1..month.lengthOfMonth()).map { month.atDay(it) }
            } else {
                testsAll.mapNotNull { parseDate(it.result_date) }.distinct().sorted()
            }

            val period = month?.let { monthLabel(it) } ?: "Barcha sanalar"
            val inPeriod = testsAll.count { t -> parseDate(t.result_date) in curColumns.toSet() }
            tvMeta.text = "${curStudents.size} ta o'quvchi • $inPeriod ta natija • $period"
            updateMonthButton()
            buildTable()
        }
    }

    private fun buildTable() {
        namesCol.removeAllViews()
        gridCol.removeAllViews()
        val hasData = curStudents.isNotEmpty() && curColumns.isNotEmpty()
        emptyState.visibility = if (hasData) View.GONE else View.VISIBLE
        tableScroll.visibility = if (hasData) View.VISIBLE else View.GONE
        if (!hasData) {
            emptyState.text = when {
                curStudents.isEmpty() ->
                    "O'quvchilar yo'q.\n«+» tugmasi bilan o'quvchi qo'shing."
                else ->
                    "Bu davrda natijalar yo'q.\nKvadratchaga bosib foiz kiriting."
            }
            return
        }

        namesCol.addView(headerCell("O'quvchi"))
        val today = LocalDate.now()
        // Sanalar sarlavhasi — bitta GORIZONTAL qator (yuqorida to'liq sanalar)
        val headerRow = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                headH
            )
        }
        curColumns.forEach { d -> headerRow.addView(columnHeader(d, today)) }
        gridCol.addView(headerRow)

        curStudents.forEachIndexed { si, st ->
            namesCol.addView(nameCell(st.full_name, si))
            val row = LinearLayout(requireContext()).apply {
                orientation = LinearLayout.HORIZONTAL
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    cellH
                )
            }
            curColumns.forEach { d -> row.addView(cellView(st, d, si)) }
            gridCol.addView(row)
        }
    }

    private fun headerCell(text: String): View {
        val box = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
            layoutParams = LinearLayout.LayoutParams(namesW, headH)
            background = cellDrawable("#1A2440", "#27355A")
            setPadding(dp(10), 0, dp(8), 0)
        }
        box.addView(TextView(requireContext()).apply {
            this.text = text
            textSize = 12.5f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(ContextCompat.getColor(context, R.color.text))
        })
        return box
    }

    /** Ustun sarlavhasi: to'liq sana (dd.MM.yyyy) + hafta kuni. */
    private fun columnHeader(date: LocalDate, today: LocalDate): View {
        val ctx = requireContext()
        val isToday = date == today
        val box = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(colW, headH).apply { marginEnd = dp(2) }
            background = if (isToday) {
                cellDrawable("#152A5A", "#2B7FFF")
            } else {
                cellDrawable("#1A2440", "#27355A")
            }
            setPadding(dp(2), 0, dp(2), 0)
        }
        box.addView(TextView(ctx).apply {
            text = date.format(dateFmt)
            textSize = 9f
            setTypeface(typeface, Typeface.BOLD)
            maxLines = 1
            setTextColor(if (isToday) ContextCompat.getColor(ctx, R.color.primary_light) else ContextCompat.getColor(ctx, R.color.text))
            gravity = Gravity.CENTER
        })
        box.addView(TextView(ctx).apply {
            text = weekShort[date.dayOfWeek.value - 1] + (if (isToday) " •" else "")
            textSize = 9f
            maxLines = 1
            setTextColor(ContextCompat.getColor(ctx, R.color.text_dim))
            gravity = Gravity.CENTER
        })
        return box
    }

    private fun nameCell(name: String, rowIndex: Int): View {
        val ctx = requireContext()
        return TextView(ctx).apply {
            text = name
            textSize = 13f
            maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
            gravity = Gravity.CENTER_VERTICAL
            setTextColor(ContextCompat.getColor(context, R.color.text))
            layoutParams = LinearLayout.LayoutParams(namesW, cellH)
            setPadding(dp(10), 0, dp(6), 0)
            if (rowIndex % 2 == 1) setBackgroundColor(Color.parseColor("#0C1425"))
        }
    }

    /** Kvadratcha katakcha: foiz yoki «—» (bosib qo'shish). */
    private fun cellView(st: Student, date: LocalDate, si: Int): View {
        val ctx = requireContext()
        val results = resultsFor(st, date)
        return TextView(ctx).apply {
            layoutParams = LinearLayout.LayoutParams(colW, cellH).apply { marginEnd = dp(2) }
            gravity = Gravity.CENTER
            textSize = 13f
            setTypeface(typeface, Typeface.BOLD)
            maxLines = 1
            if (results.isEmpty()) {
                text = "—"
                setTextColor(ContextCompat.getColor(context, R.color.text_faint))
                background = cellDrawable("#12FFFFFF", "#1C2742")
                setOnClickListener { showForm(null, st, date) }
            } else {
                val t = results.maxByOrNull { it.updated_at } ?: results.first()
                val (_, hex, _) = gradeMeta(t.percentage)
                val c = Color.parseColor(hex)
                text = "${"%.0f".format(t.percentage)}%"
                setTextColor(c)
                background = cellDrawable(alphaHex(c, 0x22), alphaHex(c, 0x77))
                setOnClickListener { showCellResults(results, st, date) }
            }
        }
    }

    private fun resultsFor(st: Student, date: LocalDate): List<TestResult> =
        testsAll.filter { it.studentUid == st.uid && parseDate(it.result_date) == date }

    // ---------- Menyular / dialoglar ----------

    /** Katakchada bitta yoki bir nechta natija bo'lishi mumkin. */
    private fun showCellResults(results: List<TestResult>, st: Student, date: LocalDate) {
        val ctx = requireContext()
        if (results.size == 1) {
            showResultOptions(results[0], st, date)
            return
        }
        val items = results.map { "${it.topic} — ${"%.0f".format(it.percentage)}%" }.toTypedArray()
        MaterialAlertDialogBuilder(ctx)
            .setTitle("${st.full_name} • ${formatDate(date)}")
            .setItems(items) { _, i -> showResultOptions(results[i], st, date) }
            .setPositiveButton("＋ Qo'shish") { _, _ -> showForm(null, st, date) }
            .setNegativeButton("Yopish", null)
            .show()
    }

    private fun showResultOptions(t: TestResult, st: Student, date: LocalDate) {
        val ctx = requireContext()
        val grade = gradeMeta(t.percentage)
        MaterialAlertDialogBuilder(ctx)
            .setTitle("${st.full_name} • ${t.topic}")
            .setMessage(
                "Sana: ${formatDate(date)}\n" +
                        "Natija: ${t.correct_answers}/${t.total_questions} (${"%.0f".format(t.percentage)}%)\n" +
                        "Baho: ${grade.first}"
            )
            .setPositiveButton("✏️ Tahrirlash") { _, _ -> showForm(t, st, date) }
            .setNegativeButton("🗑 O'chirish") { _, _ ->
                confirm(ctx, "Ushbu natija o'chirilsinmi?") {
                    lifecycleScope.launch {
                        ctx.app().repo.deleteTestResult(t.uid)
                        reload()
                    }
                }
            }
            .setNeutralButton("Yopish", null)
            .show()
    }

    /** Yangi natija yoki tahrirlash. date = qaysi sana uchun (katakchadan keladi). */
    private fun showForm(test: TestResult?, prefillStudent: Student?, date: LocalDate?) {
        val ctx = requireContext()
        lifecycleScope.launch {
            if (studentsAll.isEmpty()) {
                Toast.makeText(ctx, "Avval o'quvchi qo'shing", Toast.LENGTH_SHORT).show()
                return@launch
            }
            val b = DialogTestBinding.inflate(LayoutInflater.from(ctx))
            b.tvFormTitle.text = if (test == null) "Yangi natija" else "Natijani tahrirlash"
            val labels = studentsAll.map { it.full_name }
            b.spStudent.setAdapter(ArrayAdapter(ctx, android.R.layout.simple_list_item_1, labels))
            val defIdx = when {
                prefillStudent != null ->
                    studentsAll.indexOfFirst { it.uid == prefillStudent.uid }.takeIf { it >= 0 } ?: 0
                test != null ->
                    studentsAll.indexOfFirst { it.uid == test.studentUid }.takeIf { it >= 0 } ?: 0
                else -> 0
            }
            b.spStudent.setText(labels[defIdx], false)

            var selDate: LocalDate = date
                ?: parseDate(test?.result_date ?: "")
                ?: LocalDate.now()
            b.tvDate.text = selDate.format(dateFmt)
            b.dateRow.setOnClickListener {
                DatePickerDialog(
                    ctx,
                    { _, y, m, d ->
                        selDate = LocalDate.of(y, m + 1, d)
                        b.tvDate.text = selDate.format(dateFmt)
                    },
                    selDate.year, selDate.monthValue - 1, selDate.dayOfMonth
                ).show()
            }

            b.inTopic.setText(
                test?.topic ?: testsAll.maxByOrNull { it.updated_at }?.topic ?: "Mavzulashtirilgan test"
            )
            b.inTotal.setText(test?.total_questions?.takeIf { it > 0 }?.toString() ?: "100")
            b.inCorrect.setText(test?.correct_answers?.toString() ?: "")

            val updatePct = {
                val total = b.inTotal.text?.toString()?.toIntOrNull() ?: 0
                val correct = b.inCorrect.text?.toString()?.toIntOrNull() ?: 0
                b.tvPercent.text = if (total > 0 && correct in 0..total) {
                    val pct = correct * 100.0 / total
                    "Foiz: ${"%.0f".format(pct)}% — ${gradeMeta(pct).first}"
                } else {
                    "Foiz: —"
                }
            }
            updatePct()
            b.inTotal.addTextChangedListener(SimpleWatcher { updatePct() })
            b.inCorrect.addTextChangedListener(SimpleWatcher { updatePct() })

            val dlg = MaterialAlertDialogBuilder(ctx).setView(b.root).create()
            b.btnCancel.setOnClickListener { dlg.dismiss() }
            b.btnSave.setOnClickListener {
                var topic = b.inTopic.text?.toString()?.trim().orEmpty()
                if (topic.isEmpty()) topic = "Mavzulashtirilgan test"
                var total = b.inTotal.text?.toString()?.toIntOrNull() ?: 0
                val correct = b.inCorrect.text?.toString()?.toIntOrNull() ?: 0
                if (total <= 0 && correct in 0..100) {
                    total = 100
                }
                b.topicLayout.error = null
                if (total <= 0 || correct < 0 || correct > total) {
                    Toast.makeText(ctx, "Foiz yoki savollar sonini to'g'ri kiriting", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                lifecycleScope.launch {
                    try {
                        val si = labels.indexOf(b.spStudent.text?.toString()).takeIf { it >= 0 } ?: 0
                        val student = studentsAll[si]
                        val pct = if (total > 0) Math.round(correct * 1000.0 / total) / 10.0 else 0.0
                        if (test == null) {
                            ctx.app().repo.addTestResult(
                                student.uid, topic, total, correct,
                                selDate.toString(), ""
                            )
                        } else {
                            ctx.app().repo.updateTestResult(test.copy(
                                studentUid = student.uid, studentId = student.id,
                                topic = topic, total_questions = total, correct_answers = correct,
                                percentage = pct, result_date = selDate.toString()
                            ))
                        }
                        dlg.dismiss()
                        reload()
                    } catch (e: Exception) {
                        Toast.makeText(ctx, "Xato: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
            dlg.show()
        }
    }

    // ---------- PDF ----------

    private fun printPdf() {
        if (curStudents.isEmpty() || curColumns.isEmpty()) {
            Toast.makeText(requireContext(), "Chop etish uchun natijalar yo'q", Toast.LENGTH_SHORT).show()
            return
        }
        val ctx = requireContext()
        val cells: List<List<Double?>> = curStudents.map { st ->
            curColumns.map { d ->
                resultsFor(st, d).maxByOrNull { it.updated_at }?.percentage
            }
        }
        val period = selectedMonth?.let { monthLabel(it) } ?: "Barcha sanalar"
        val pm = ctx.getSystemService(Context.PRINT_SERVICE) as PrintManager
        val attrs = PrintAttributes.Builder()
            .setMediaSize(PrintAttributes.MediaSize.ISO_A4)
            .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
            .build()
        pm.print("KursManager_Test_natijalari",
            TestsPrintAdapter(curStudents.map { it.full_name }, curColumns, cells, period), attrs)
    }

    // ---------- Yordamchi ----------

    private fun parseDate(iso: String): LocalDate? = try {
        LocalDate.parse(iso.take(10))
    } catch (e: Exception) {
        null
    }

    private val LocalDate.yearMonth: YearMonth get() = YearMonth.from(this)

    private fun formatDate(d: LocalDate): String = d.format(dateFmt)

    private fun cellDrawable(fill: String, stroke: String): android.graphics.drawable.GradientDrawable =
        android.graphics.drawable.GradientDrawable().apply {
            shape = android.graphics.drawable.GradientDrawable.RECTANGLE
            cornerRadius = 10f * resources.displayMetrics.density
            setColor(Color.parseColor(fill))
            setStroke(1, Color.parseColor(stroke))
        }

    private fun alphaHex(c: Int, alpha: Int): String {
        val a = String.format("%02X", alpha)
        return "#${a}${String.format("%06X", c and 0x00FFFFFF)}"
    }
}
