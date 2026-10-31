package uz.kursmanager.ui

import android.app.DatePickerDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.checkbox.MaterialCheckBox
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.data.Student
import uz.kursmanager.databinding.DialogStudentBinding
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Calendar

private const val DEFAULT_COURSE = "Kimyo kursi"

class StudentsFragment : Fragment() {

    private lateinit var adapter: RowAdapter
    private var all: List<Student> = emptyList()
    private var courseNames: Map<String, String> = emptyMap()

    private val gradeLabels = listOf("Tanlanmagan", "7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf")
    private val dateFmt = DateTimeFormatter.ofPattern("dd.MM.yyyy")

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_list, c, false)
        val list = v.findViewById<RecyclerView>(R.id.list)
        list.layoutManager = LinearLayoutManager(context)
        adapter = RowAdapter(emptyList()) { row, act -> onAction(row.key, act) }
        list.adapter = adapter
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showEdit(null) }
        v.findViewById<EditText>(R.id.inSearch).apply {
            hint = "F.I.Sh yoki telefon..."
            addTextChangedListener(SimpleWatcher { reload(filter = it) })
        }
        reload()
        return v
    }

    private fun reload(filter: String = "") {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            courseNames = repo.courses().associate { it.uid to it.name }
            val groups = repo.groups()
            val gNamesByStudent = repo.allGroupMembers()
                .groupBy({ it.studentUid }, { it.groupUid })
                .mapValues { (_, uids) ->
                    uids.mapNotNull { uid -> groups.find { it.uid == uid }?.name }.filter { it.isNotEmpty() }
                }
            all = repo.students()
            val f = filter.trim().lowercase()
            val rows = all.filter {
                f.isEmpty() || it.full_name.lowercase().contains(f) || it.phone.contains(f)
            }.map { st ->
                val (bt, bc) = payStatusMeta(st.payment_status)
                val sub = listOfNotNull(
                    st.phone.ifEmpty { null },
                    gNamesByStudent[st.uid]?.joinToString(", ")?.ifEmpty { null },
                    courseNames[st.courseUid]
                ).joinToString(" • ").ifEmpty { "—" }
                RowAdapter.RowData(st.uid, st.full_name, sub, bt, bc, studentMenu(st.payment_status))
            }
            adapter.setData(rows)
        }
    }

    private fun onAction(uid: String, act: String) {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            val st = repo.students().find { it.uid == uid } ?: return@launch
            when {
                act == "detail" -> showDetail(st)
                act == "edit" -> showEdit(st)
                act == "delete" -> confirm(requireContext(), "Ushbu o'quvchini o'chirishni xohlaysizmi?") {
                    lifecycleScope.launch { repo.deleteStudent(uid); reload() }
                }
                act.startsWith("status:") -> {
                    repo.setPaymentStatus(uid, act.substringAfter(":"))
                    reload()
                }
            }
        }
    }

    private fun showDetail(st: Student) {
        val feeTxt = if (st.fee > 0) "%,.0f so'm".format(st.fee).replace(",", " ") else "—"
        val grade = st.grade.ifEmpty { "—" }
        val joined = parseIsoDate(st.created_at)?.format(dateFmt) ?: "—"
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            val gUids = repo.studentGroupUids(st.uid)
            val gNames = repo.groups().filter { it.uid in gUids }.joinToString(", ") { it.name }
            MaterialAlertDialogBuilder(requireContext())
                .setTitle(st.full_name)
                .setMessage("Sinf: $grade\nGuruh: ${gNames.ifEmpty { "—" }}\nKelgan sana: $joined\nTelefon: ${st.phone.ifEmpty { "—" }}\nKurs: ${courseNames[st.courseUid] ?: "—"}\nSumma: $feeTxt\nHolat: ${payStatusMeta(st.payment_status).first}\nIzoh: ${st.note.ifEmpty { "—" }}")
                .setPositiveButton("Tahrirlash") { _, _ -> showEdit(st) }
                .setNeutralButton("Yopish", null)
                .show()
        }
    }

    private fun showEdit(st: Student?) {
        val ctx = requireContext()
        lifecycleScope.launch {
            val repo = ctx.app().repo
            val courses = repo.courses()
            val groups = repo.groups()
            val curGroupUids = st?.let { repo.studentGroupUids(it.uid) } ?: emptySet()
            val b = DialogStudentBinding.inflate(LayoutInflater.from(ctx))
            b.tvFormTitle.text = if (st == null) "Yangi o'quvchi" else "Tahrirlash"

            // Kurs: "Kurssiz" olib tashlandi — doimiy «Kimyo kursi» (o'zgartirib bo'lmaydi)
            val courseLabels = courses.map { it.name }
            b.spCourse.setAdapter(ArrayAdapter(ctx, android.R.layout.simple_list_item_1, courseLabels))
            val currentCourseName = st?.courseUid?.let { su -> courses.find { it.uid == su }?.name }
            val defaultCourseName = currentCourseName
                ?: courses.find { it.name.contains("kimyo", ignoreCase = true) }?.name
                ?: DEFAULT_COURSE
            b.spCourse.setText(defaultCourseName, false)
            b.spCourse.isFocusable = false
            b.spCourse.isClickable = false
            b.spCourse.keyListener = null

            b.spGrade.setAdapter(ArrayAdapter(ctx, android.R.layout.simple_list_item_1, gradeLabels))
            val curGi = gradeLabels.indexOf(st?.grade ?: "").takeIf { it >= 0 } ?: 0
            b.spGrade.setText(gradeLabels[curGi], false)

            val pad = (2 * ctx.resources.displayMetrics.density).toInt()
            b.groupsBox.removeAllViews()
            if (groups.isEmpty()) {
                b.groupsBox.addView(TextView(ctx).apply {
                    text = "Avval «Guruhlar» bo'limida guruh yarating."
                    setTextColor(ContextCompat.getColor(ctx, R.color.text_dim))
                    textSize = 13f
                })
            }
            val groupChecks = mutableListOf<Pair<String, MaterialCheckBox>>()
            for (g in groups) {
                val cb = MaterialCheckBox(ctx).apply {
                    text = "👥  ${g.name}"
                    textSize = 15f
                    isChecked = g.uid in curGroupUids
                    setTextColor(ContextCompat.getColor(ctx, R.color.text))
                    setPadding(0, pad, 0, pad)
                }
                b.groupsBox.addView(cb)
                groupChecks.add(g.uid to cb)
            }

            var pickedDate: LocalDate = parseIsoDate(st?.created_at) ?: LocalDate.now()
            b.inDate.setText(pickedDate.format(dateFmt))
            b.inDate.setOnClickListener {
                val cal = Calendar.getInstance().apply {
                    set(pickedDate.year, pickedDate.monthValue - 1, pickedDate.dayOfMonth)
                }
                DatePickerDialog(ctx, { _, y, m, d ->
                    pickedDate = LocalDate.of(y, m + 1, d)
                    b.inDate.setText(pickedDate.format(dateFmt))
                }, cal.get(Calendar.YEAR), cal.get(Calendar.MONTH), cal.get(Calendar.DAY_OF_MONTH)).show()
            }

            val keys = listOf("paid", "pending", "unpaid")
            val statusBtns = listOf(b.btnPaid, b.btnPending, b.btnUnpaid)
            val curSi = keys.indexOf(st?.payment_status ?: "unpaid").takeIf { it >= 0 } ?: 2
            b.tgStatus.check(statusBtns[curSi].id)

            b.inName.setText(st?.full_name ?: "")
            b.inPhone.setText(st?.phone ?: "")
            b.inFee.setText(if ((st?.fee ?: 0.0) > 0) st!!.fee.toInt().toString() else "")
            b.inNote.setText(st?.note ?: "")

            val dlg = MaterialAlertDialogBuilder(ctx).setView(b.root).create()
            b.btnCancel.setOnClickListener { dlg.dismiss() }
            b.btnSave.setOnClickListener {
                val name = b.inName.text?.toString()?.trim().orEmpty()
                if (name.length < 3) {
                    b.nameLayout.error = "F.I.Sh kiritilishi kerak"
                    b.inName.requestFocus()
                    return@setOnClickListener
                }
                b.nameLayout.error = null
                val courseName = b.spCourse.text?.toString()?.trim()
                    ?.takeIf { it.isNotEmpty() } ?: DEFAULT_COURSE
                val status = when (b.tgStatus.checkedButtonId) {
                    b.btnPaid.id -> "paid"
                    b.btnPending.id -> "pending"
                    else -> "unpaid"
                }
                val fee = b.inFee.text?.toString()?.toDoubleOrNull() ?: 0.0
                val phone = b.inPhone.text?.toString()?.trim().orEmpty()
                val note = b.inNote.text?.toString()?.trim().orEmpty()
                val grade = b.spGrade.text?.toString()?.trim().orEmpty()
                    .takeIf { it.isNotEmpty() && it != "Tanlanmagan" } ?: ""
                val createdAt = pickedDate.toString()
                val pickedGroups = groupChecks.filter { it.second.isChecked }.map { it.first }.toSet()
                lifecycleScope.launch {
                    try {
                        val course = repo.ensureCourse(courseName)
                        if (st == null) {
                            val saved = repo.addStudent(name, phone, course.uid,
                                status, fee, note, grade, createdAt)
                            repo.setStudentGroups(saved.uid, pickedGroups)
                        } else {
                            repo.updateStudent(st.copy(
                                full_name = name, phone = phone,
                                courseId = course.id, courseUid = course.uid,
                                payment_status = status, fee = fee, note = note,
                                grade = grade, created_at = createdAt))
                            repo.setStudentGroups(st.uid, pickedGroups)
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

    private fun parseIsoDate(raw: String?): LocalDate? {
        if (raw.isNullOrBlank() || raw.length < 10) return null
        return try { LocalDate.parse(raw.substring(0, 10)) } catch (e: Exception) { null }
    }
}

class SimpleWatcher(val fn: (String) -> Unit) : android.text.TextWatcher {
    override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
    override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) { fn(s?.toString() ?: "") }
    override fun afterTextChanged(s: android.text.Editable?) {}
}
