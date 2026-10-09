package uz.kursmanager.ui

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.data.Student
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter

class AttendanceFragment : Fragment() {

    private var weekOffset = 0
    private lateinit var table: TableLayout
    private lateinit var weekLabel: TextView
    private var students: List<Student> = emptyList()
    private val fmt = DateTimeFormatter.ofPattern("dd.MM")
    private val wdays = listOf("Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya")

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val root = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#080D19"))
            val p = (14 * resources.displayMetrics.density).toInt()
            setPadding(p, p, p, p)
        }
        val nav = LinearLayout(requireContext()).apply { orientation = LinearLayout.HORIZONTAL }
        val bPrev = Button(requireContext()).apply { text = "‹"; setOnClickListener { weekOffset--; load() } }
        val bToday = Button(requireContext()).apply { text = "Bugun"; setOnClickListener { weekOffset = 0; load() } }
        val bNext = Button(requireContext()).apply { text = "›"; setOnClickListener { weekOffset++; load() } }
        nav.addView(bPrev); nav.addView(bToday); nav.addView(bNext)
        weekLabel = TextView(requireContext()).apply {
            setTextColor(Color.parseColor("#93A1BD")); textSize = 13f
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            layoutParams = lp; gravity = Gravity.END
        }
        nav.addView(weekLabel)
        table = TableLayout(requireContext()).apply { isStretchAllColumns = false }
        val sv = android.widget.HorizontalScrollView(requireContext())
        sv.addView(table)
        root.addView(nav); root.addView(sv)

        val saveBtn = Button(requireContext()).apply {
            text = "Davomatni saqlash"
            textSize = 15f
            isAllCaps = false
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.parseColor("#189A52"))
            val m = (14 * resources.displayMetrics.density).toInt()
            setPadding(m, m, m, m)
        }
        val btnLp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = (10 * resources.displayMetrics.density).toInt() }
        root.addView(saveBtn, btnLp)

        saveBtn.setOnClickListener {
            saveBtn.isEnabled = false
            saveBtn.text = "Saqlanmoqda..."
            lifecycleScope.launch {
                try {
                    val r = requireContext().app().sync.fullSync().getOrThrow()
                    Toast.makeText(requireContext(),
                        "Davomat saqlandi va sinxron qilindi (yuborildi: ${r.pushed}, olindi: ${r.pulled})",
                        Toast.LENGTH_LONG).show()
                    load()
                } catch (e: Exception) {
                    Toast.makeText(requireContext(),
                        "Saqlanmadi: ${e.message ?: "kompyuterga ulanib bo'lmadi"}. Avval juftlang.",
                        Toast.LENGTH_LONG).show()
                } finally {
                    saveBtn.isEnabled = true
                    saveBtn.text = "Davomatni saqlash"
                }
            }
        }

        load()
        return root
    }

    private fun weekDates(): List<LocalDate> {
        var monday = LocalDate.now().with(DayOfWeek.MONDAY).plusWeeks(weekOffset.toLong())
        return (0..6).map { monday.plusDays(it.toLong()) }
    }

    private fun load() {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            students = repo.students()
            val dates = weekDates()
            weekLabel.text = "${dates.first().format(fmt)} — ${dates.last().format(DateTimeFormatter.ofPattern("dd.MM.yyyy"))}"
            val all = repo.attendanceRange(dates.first().toString(), dates.last().toString())
            val lookup = all.associate { it.studentId to it.att_date to it.present }
            table.removeAllViews()
            // sarlavha
            val head = TableRow(requireContext())
            head.addView(hcell("F.I.Sh", true))
            dates.forEach { d ->
                head.addView(hcell("${wdays[d.dayOfWeek.value - 1]}\n${d.format(fmt)}", true))
            }
            head.addView(hcell("%", true))
            table.addView(head)
            // qatorlar
            for (st in students) {
                val row = TableRow(requireContext())
                row.addView(hcell(st.full_name, false))
                var p = 0; var m = 0
                dates.forEach { d ->
                    val v = lookup[st.id to d.toString()]
                    if (v == true) p++ else if (v == false) m++
                    val cell = TextView(requireContext()).apply {
                        text = when (v) { true -> "✓"; false -> "✗"; else -> "—" }
                        gravity = Gravity.CENTER
                        textSize = 18f
                        setTypeface(typeface, Typeface.BOLD)
                        setPadding(18, 18, 18, 18)
                        setTextColor(Color.WHITE)
                        background = android.graphics.drawable.GradientDrawable().apply {
                            shape = android.graphics.drawable.GradientDrawable.RECTANGLE
                            cornerRadius = 20f
                            setColor(Color.parseColor(when (v) { true -> "#189A52"; false -> "#E0324B"; else -> "#131C33" }))
                        }
                        setOnClickListener {
                            lifecycleScope.launch {
                                val cur = repo.attendanceOne(st.id, d.toString())
                                val next = when (cur?.present) { null -> true; true -> false; false -> null }
                                repo.setAttendance(st.uid, d.toString(), next)
                                load()
                            }
                        }
                    }
                    row.addView(cell)
                }
                val pct = if (p + m == 0) 0 else p * 100 / (p + m)
                row.addView(hcell("$pct%", false))
                table.addView(row)
            }
        }
    }

    private fun hcell(t: String, head: Boolean): TextView {
        return TextView(requireContext()).apply {
            text = t
            textSize = if (head) 11f else 14f
            setTextColor(Color.parseColor(if (head) "#5B6B8C" else "#E8EEF7"))
            if (!head) setTypeface(typeface, Typeface.BOLD)
            setPadding(14, 18, 14, 18)
        }
    }
}
