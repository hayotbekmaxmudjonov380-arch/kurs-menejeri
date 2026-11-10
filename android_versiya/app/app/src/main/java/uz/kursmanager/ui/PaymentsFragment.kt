package uz.kursmanager.ui

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TableLayout
import android.widget.TableRow
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.data.Group
import uz.kursmanager.data.GroupMember
import uz.kursmanager.data.Student
import java.time.LocalDate

class PaymentsFragment : Fragment() {

    private var selectedYear = LocalDate.now().year
    private lateinit var table: TableLayout
    private lateinit var yearLabel: TextView
    private var students: List<Student> = emptyList()
    private var groups: List<Group> = emptyList()
    private var memberships: List<GroupMember> = emptyList()
    private var selectedGroupUid: String? = null
    private var spinnerUids: List<String?> = emptyList()
    private var spinnerLabels: List<String> = emptyList()
    private lateinit var groupSpin: Spinner
    private val monthNames = listOf("Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek")

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val root = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#080D19"))
            val p = (14 * resources.displayMetrics.density).toInt()
            setPadding(p, p, p, p)
        }
        val nav = LinearLayout(requireContext()).apply { orientation = LinearLayout.HORIZONTAL }
        val bPrev = Button(requireContext()).apply { text = "‹"; setOnClickListener { selectedYear--; load() } }
        val bToday = Button(requireContext()).apply { text = "Joriy yil"; setOnClickListener { selectedYear = LocalDate.now().year; load() } }
        val bNext = Button(requireContext()).apply { text = "›"; setOnClickListener { selectedYear++; load() } }
        nav.addView(bPrev); nav.addView(bToday); nav.addView(bNext)
        yearLabel = TextView(requireContext()).apply {
            setTextColor(Color.parseColor("#93A1BD")); textSize = 15f
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            layoutParams = lp; gravity = Gravity.END
        }
        nav.addView(yearLabel)
        table = TableLayout(requireContext()).apply { isStretchAllColumns = false }
        val sv = android.widget.HorizontalScrollView(requireContext())
        sv.addView(table)
        root.addView(nav)

        groupSpin = Spinner(requireContext())
        val spinLp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = (8 * resources.displayMetrics.density).toInt() }
        root.addView(groupSpin, spinLp)
        groupSpin.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val uid = spinnerUids.getOrElse(position) { null }
                if (uid == selectedGroupUid) return
                selectedGroupUid = uid
                load()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        root.addView(sv)

        val saveBtn = Button(requireContext()).apply {
            text = "To'lovni saqlash va sinxronlash"
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
                        "To'lovlar saqlandi va sinxron qilindi (yuborildi: ${r.pushed}, olindi: ${r.pulled})",
                        Toast.LENGTH_LONG).show()
                    load()
                } catch (e: Exception) {
                    Toast.makeText(requireContext(),
                        "Saqlanmadi: ${e.message ?: "kompyuterga ulanib bo'lmadi"}. Avval juftlang.",
                        Toast.LENGTH_LONG).show()
                } finally {
                    saveBtn.isEnabled = true
                    saveBtn.text = "To'lovni saqlash va sinxronlash"
                }
            }
        }

        load()
        return root
    }

    private fun load() {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            students = repo.students()
            groups = repo.groups().sortedBy { it.name.lowercase() }
            memberships = repo.allGroupMembers()
            updateGroupSpinner()
            yearLabel.text = "$selectedYear-yil to'lovlar"
            val all = repo.monthlyPaymentsYear(selectedYear)
            val lookup = all.associate { (it.studentId ?: 0L) to it.month to it.paid }
            table.removeAllViews()

            val head = TableRow(requireContext())
            head.addView(hcell("F.I.Sh", true))
            monthNames.forEach { m ->
                head.addView(hcell(m, true))
            }
            head.addView(hcell("Jami", true))
            table.addView(head)

            var rendered = 0
            for ((secTitle, secList) in buildSections()) {
                if (secTitle != null) table.addView(sectionRow(secTitle, 14))
                for (st in secList) {
                    val row = TableRow(requireContext())
                    row.addView(hcell(st.full_name, false))
                    var paidCount = 0
                    for (m in 1..12) {
                        val v = lookup[st.id to m]
                        if (v == true) paidCount++
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
                                    val cur = repo.monthlyPaymentOne(st.id, selectedYear, m)
                                    val next = when (cur?.paid) { null -> true; true -> false; false -> null }
                                    repo.setMonthlyPayment(st.uid, selectedYear, m, next, st.fee)
                                    load()
                                }
                            }
                        }
                        row.addView(cell)
                    }
                    row.addView(hcell("$paidCount/12", false))
                    table.addView(row)
                    rendered++
                }
            }
            if (rendered == 0) {
                table.addView(infoRow("O'quvchilar yo'q"))
            }
        }
    }

    private fun buildSections(): List<Pair<String?, List<Student>>> {
        val sel = selectedGroupUid
        if (sel != null) {
            val uids = memberships.filter { it.groupUid == sel }.map { it.studentUid }.toSet()
            return listOf(null to students.filter { it.uid in uids })
        }
        if (groups.isEmpty()) return listOf(null to students)
        val sections = mutableListOf<Pair<String?, List<Student>>>()
        val grouped = mutableSetOf<String>()
        for (g in groups) {
            val uids = memberships.filter { it.groupUid == g.uid }.map { it.studentUid }.toSet()
            val list = students.filter { it.uid in uids }
            if (list.isNotEmpty()) {
                sections.add(g.name to list)
                grouped.addAll(uids)
            }
        }
        val rest = students.filter { it.uid !in grouped }
        if (rest.isNotEmpty()) sections.add("Guruhsiz" to rest)
        if (sections.isEmpty()) return listOf(null to students)
        return sections
    }

    private fun sectionRow(title: String, spanCount: Int): TableRow {
        val row = TableRow(requireContext())
        val cell = TextView(requireContext()).apply {
            text = "▣  $title"
            textSize = 13f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(Color.parseColor("#5B9BFF"))
            gravity = Gravity.CENTER_VERTICAL
            setPadding(14, 18, 14, 18)
        }
        val lp = TableRow.LayoutParams(TableRow.LayoutParams.MATCH_PARENT, TableRow.LayoutParams.WRAP_CONTENT)
        lp.span = spanCount
        row.addView(cell, lp)
        return row
    }

    private fun infoRow(text: String): TableRow {
        val row = TableRow(requireContext())
        val cell = TextView(requireContext()).apply {
            this.text = text
            textSize = 14f
            setTextColor(Color.parseColor("#93A1BD"))
            gravity = Gravity.CENTER
            setPadding(14, 48, 14, 48)
        }
        val lp = TableRow.LayoutParams(TableRow.LayoutParams.MATCH_PARENT, TableRow.LayoutParams.WRAP_CONTENT)
        lp.span = 14
        row.addView(cell, lp)
        return row
    }

    private fun updateGroupSpinner() {
        val labels = listOf("Barcha guruhlar") + groups.map { it.name }
        val uids = listOf<String?>(null) + groups.map { it.uid }
        spinnerUids = uids
        if (selectedGroupUid != null && selectedGroupUid !in uids) selectedGroupUid = null
        if (labels != spinnerLabels) {
            spinnerLabels = labels
            val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, labels)
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            groupSpin.adapter = adapter
            groupSpin.setSelection(uids.indexOf(selectedGroupUid).coerceAtLeast(0))
        }
    }

    private fun file_cell(t: String, head: Boolean) = hcell(t, head)

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
