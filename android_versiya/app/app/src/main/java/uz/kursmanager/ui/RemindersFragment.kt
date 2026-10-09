package uz.kursmanager.ui

import android.app.DatePickerDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
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
import uz.kursmanager.databinding.DialogReminderBinding
import uz.kursmanager.sync.cancelReminderAlarm
import uz.kursmanager.sync.scheduleReminderAlarm
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Calendar

class RemindersFragment : Fragment() {

    private lateinit var adapter: RowAdapter

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_list, c, false)
        val list = v.findViewById<RecyclerView>(R.id.list)
        list.layoutManager = LinearLayoutManager(context)
        adapter = RowAdapter(emptyList()) { row, act -> onAction(row.key, act) }
        list.adapter = adapter
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showAdd() }
        v.findViewById<EditText>(R.id.inSearch).visibility = View.GONE
        reload()
        return v
    }

    private fun reload() {
        lifecycleScope.launch {
            val rows = requireContext().app().repo.reminders().map { r ->
                val (bt, bc) = if (r.is_done) "✓ Bajarildi" to "#22C55E" else "◷ Kutilmoqda" to "#F5A80B"
                RowAdapter.RowData(r.uid, r.title,
                    r.remind_at.replace("T", " ").take(16) + (if (r.note.isNotEmpty()) " • ${r.note}" else ""),
                    bt, bc, listOf("done" to if (r.is_done) "Bajarilmagan qilish" else "Bajarildi qilish", "delete" to "O'chirish"))
            }
            adapter.setData(rows)
        }
    }

    private fun onAction(uid: String, act: String) {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            when (act) {
                "done" -> {
                    val cur = repo.reminders().find { it.uid == uid } ?: return@launch
                    repo.setReminderDone(uid, !cur.is_done)
                    if (!cur.is_done) cancelReminderAlarm(requireContext(), uid)
                    reload()
                }
                "delete" -> confirm(requireContext(), "Eslatmani o'chirishni xohlaysizmi?") {
                    lifecycleScope.launch {
                        cancelReminderAlarm(requireContext(), uid)
                        repo.deleteReminder(uid); reload()
                    }
                }
            }
        }
    }

    private fun showAdd() {
        val ctx = requireContext()
        val b = DialogReminderBinding.inflate(layoutInflater)
        b.inDate.setText(LocalDateTime.now().plusDays(1).format(DateTimeFormatter.ofPattern("yyyy-MM-dd")))
        b.inTime.setText("09:00")
        b.inDate.setOnClickListener {
            val c = Calendar.getInstance()
            DatePickerDialog(ctx, { _, y, m, d ->
                b.inDate.setText("%04d-%02d-%02d".format(y, m + 1, d))
            }, c.get(Calendar.YEAR), c.get(Calendar.MONTH), c.get(Calendar.DAY_OF_MONTH)).show()
        }
        b.inTime.setOnClickListener {
            android.app.TimePickerDialog(ctx, { _, h, mi ->
                b.inTime.setText("%02d:%02d".format(h, mi))
            }, 9, 0, true).show()
        }

        val dlg = MaterialAlertDialogBuilder(ctx).setView(b.root).create()
        b.btnCancel.setOnClickListener { dlg.dismiss() }
        b.btnSave.setOnClickListener {
            val title = b.inTitle.text?.toString()?.trim().orEmpty()
            if (title.isEmpty()) {
                b.titleLayout.error = "Sarlavhani kiriting"
                b.inTitle.requestFocus()
                return@setOnClickListener
            }
            b.titleLayout.error = null
            val date = b.inDate.text?.toString()?.trim().orEmpty()
            val time = b.inTime.text?.toString()?.trim().orEmpty().ifEmpty { "09:00" }
            val note = b.inNote.text?.toString()?.trim().orEmpty()
            val iso = "${date}T${time}:00.000000"
            lifecycleScope.launch {
                try {
                    ctx.app().repo.addReminder(title, note, iso)
                    val added = ctx.app().repo.reminders().find {
                        it.title == title && it.remind_at == iso
                    }
                    if (added != null) scheduleReminderAlarm(ctx, added.uid, title, note, iso)
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
