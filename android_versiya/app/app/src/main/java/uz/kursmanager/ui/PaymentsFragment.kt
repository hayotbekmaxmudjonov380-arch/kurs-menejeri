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
import uz.kursmanager.databinding.DialogPaymentBinding
import java.time.LocalDate

class PaymentsFragment : Fragment() {

    private lateinit var adapter: RowAdapter

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_list, c, false)
        val list = v.findViewById<RecyclerView>(R.id.list)
        list.layoutManager = LinearLayoutManager(context)
        adapter = RowAdapter(emptyList()) { row, act -> onAction(row.key, act) }
        list.adapter = adapter
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showAdd() }
        v.findViewById<EditText>(R.id.inSearch).apply {
            hint = "F.I.Sh yoki telefon..."
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
            val rows = repo.recentPayments().filter { p ->
                val st = students[p.studentUid]
                f.isEmpty() || (st?.full_name?.lowercase()?.contains(f) == true) || (st?.phone?.contains(f) == true)
            }.map { p ->
                val st = students[p.studentUid]
                val (bt, bc) = payStatusMeta(p.status)
                val amt = "%,.0f so'm".format(p.amount).replace(",", " ")
                RowAdapter.RowData(p.uid, st?.full_name ?: "—",
                    "${p.payment_date.take(10)} • $amt", bt, bc, simpleMenu())
            }
            adapter.setData(rows)
        }
    }

    private fun onAction(uid: String, act: String) {
        if (act == "delete") confirm(requireContext(), "Ushbu to'lovni o'chirishni xohlaysizmi?") {
            lifecycleScope.launch { requireContext().app().repo.deletePayment(uid); reload() }
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
            val b = DialogPaymentBinding.inflate(layoutInflater)
            val labels = students.map { st ->
                if (st.phone.isBlank()) st.full_name else "${st.full_name} • ${st.phone}"
            }
            b.spStudent.setAdapter(ArrayAdapter(ctx, android.R.layout.simple_list_item_1, labels))
            b.spStudent.setText(labels[0], false)
            b.inDate.setText(LocalDate.now().toString())

            val dlg = MaterialAlertDialogBuilder(ctx).setView(b.root).create()
            b.btnCancel.setOnClickListener { dlg.dismiss() }
            b.btnSave.setOnClickListener {
                val amt = b.inAmount.text?.toString()?.toDoubleOrNull() ?: 0.0
                if (amt <= 0) {
                    b.amountLayout.error = "Summani kiriting"
                    b.inAmount.requestFocus()
                    return@setOnClickListener
                }
                b.amountLayout.error = null
                val si = labels.indexOf(b.spStudent.text?.toString()).takeIf { it >= 0 } ?: 0
                val date = b.inDate.text?.toString()?.trim().orEmpty().ifEmpty { LocalDate.now().toString() }
                lifecycleScope.launch {
                    try {
                        ctx.app().repo.addPayment(students[si].uid, amt, "paid", date, "")
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
