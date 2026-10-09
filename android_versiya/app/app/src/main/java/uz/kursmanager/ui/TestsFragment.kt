package uz.kursmanager.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.databinding.DialogTestBinding
import java.time.LocalDate

class TestsFragment : Fragment() {

    private lateinit var adapter: RowAdapter

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_list, c, false)
        val list = v.findViewById<RecyclerView>(R.id.list)
        list.layoutManager = LinearLayoutManager(context)
        adapter = RowAdapter(emptyList()) { row, act -> onAction(row.key, act) }
        list.adapter = adapter
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showAdd() }
        v.findViewById<EditText>(R.id.inSearch).apply {
            hint = "Mavzu yoki F.I.Sh..."
            addTextChangedListener(SimpleWatcher { reload(it) })
        }
        reload()
        return v
    }

    private fun reload(filter: String = "") {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            val students = repo.students().associateBy { it.uid }
            val f = filter.trim().lowercase()
            val rows = repo.testResults().filter { t ->
                f.isEmpty() || t.topic.lowercase().contains(f) ||
                        (students[t.studentUid]?.full_name?.lowercase()?.contains(f) == true)
            }.map { t ->
                val (g, gc, _) = gradeMeta(t.percentage)
                RowAdapter.RowData(t.uid, t.topic,
                    "${students[t.studentUid]?.full_name ?: "—"} • ${t.correct_answers}/${t.total_questions} • ${t.percentage}%",
                    g, gc, simpleMenu())
            }
            adapter.setData(rows)
        }
    }

    private fun onAction(uid: String, act: String) {
        if (act == "delete") confirm(requireContext(), "Ushbu natijani o'chirishni xohlaysizmi?") {
            lifecycleScope.launch { requireContext().app().repo.deleteTestResult(uid); reload() }
        }
    }

    private fun showAdd() {
        val ctx = requireContext()
        lifecycleScope.launch {
            val students = ctx.app().repo.students()
            if (students.isEmpty()) {
                Toast.makeText(ctx, "Avval o'quvchi qo'shing", Toast.LENGTH_SHORT).show()
                return@launch
            }
            val b = DialogTestBinding.inflate(layoutInflater)
            val labels = students.map { it.full_name }
            b.spStudent.setAdapter(ArrayAdapter(ctx, android.R.layout.simple_list_item_1, labels))
            b.spStudent.setText(labels[0], false)

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
            b.inTotal.addTextChangedListener(SimpleWatcher { updatePct() })
            b.inCorrect.addTextChangedListener(SimpleWatcher { updatePct() })

            val dlg = MaterialAlertDialogBuilder(ctx).setView(b.root).create()
            b.btnCancel.setOnClickListener { dlg.dismiss() }
            b.btnSave.setOnClickListener {
                val topic = b.inTopic.text?.toString()?.trim().orEmpty()
                val total = b.inTotal.text?.toString()?.toIntOrNull() ?: 0
                val correct = b.inCorrect.text?.toString()?.toIntOrNull() ?: 0
                if (topic.isEmpty()) {
                    b.topicLayout.error = "Mavzuni kiriting"
                    b.inTopic.requestFocus()
                    return@setOnClickListener
                }
                b.topicLayout.error = null
                if (total <= 0 || correct < 0 || correct > total) {
                    Toast.makeText(ctx, "Savollar sonini to'g'ri kiriting", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                lifecycleScope.launch {
                    try {
                        val si = labels.indexOf(b.spStudent.text?.toString()).takeIf { it >= 0 } ?: 0
                        ctx.app().repo.addTestResult(students[si].uid, topic, total, correct,
                            LocalDate.now().toString(), "")
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
}
