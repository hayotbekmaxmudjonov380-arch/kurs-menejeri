package uz.kursmanager.ui

import android.graphics.Rect
import android.os.Bundle
import android.text.InputType
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.data.Group

class GroupsFragment : Fragment() {

    private lateinit var adapter: GroupCardAdapter
    private var all: List<Group> = emptyList()

    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_list, c, false)
        val list = v.findViewById<RecyclerView>(R.id.list)
        // Kartochkali grid: telefonda 2 ustun, katta ekranda ko'proq
        val widthDp = (resources.displayMetrics.widthPixels / resources.displayMetrics.density).toInt()
        val cols = (widthDp / 170).coerceAtLeast(1)
        list.layoutManager = GridLayoutManager(context, cols)
        // Kartochkalar orasidagi teng masofa (chetlarda yarmi — simmetriya uchun)
        val sp = (12 * resources.displayMetrics.density).toInt()
        list.addItemDecoration(object : RecyclerView.ItemDecoration() {
            override fun getItemOffsets(
                outRect: Rect, view: View, parent: RecyclerView, state: RecyclerView.State
            ) {
                outRect.left = sp / 2
                outRect.right = sp / 2
                outRect.bottom = sp
            }
        })
        adapter = GroupCardAdapter(
            emptyList(),
            onClick = { card -> showMembers(card.uid) },
            onMenu = { card, act -> onAction(card.uid, act) }
        )
        list.adapter = adapter
        v.findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener { showEdit(null) }
        v.findViewById<EditText>(R.id.inSearch).apply {
            hint = "Guruh nomi..."
            addTextChangedListener(SimpleWatcher { reload(it) })
        }
        reload()
        return v
    }

    private fun reload(filter: String = "") {
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            all = repo.groups()
            val f = filter.trim().lowercase()
            val cards = all
                .filter { f.isEmpty() || it.name.lowercase().contains(f) }
                .map { g ->
                    val count = repo.groupMemberCount(g.uid)
                    GroupCardAdapter.GroupCardData(
                        g.uid, g.name,
                        "$count ta o'quvchi • ${g.created_at.take(10)}",
                        badgeText = if (count > 0) "$count kishi" else "bo'sh",
                        badgeColor = if (count > 0) "#22C55E" else "#64748B",
                        menu = listOf(
                            "members" to "👥 A'zolar",
                            "edit" to "✏️ Nomini tahrirlash",
                            "delete" to "🗑 O'chirish"
                        )
                    )
                }
            adapter.setData(cards)
        }
    }

    private fun onAction(uid: String, act: String) {
        when (act) {
            "members" -> showMembers(uid)
            "edit" -> showEdit(all.find { it.uid == uid })
            "delete" -> confirm(requireContext(), "Guruhni o'chirishni xohlaysizmi? O'quvchilar o'chmaydi.") {
                lifecycleScope.launch {
                    requireContext().app().repo.deleteGroup(uid)
                    reload()
                }
            }
        }
    }

    private fun showEdit(g: Group?) {
        val ctx = requireContext()
        val input = EditText(ctx).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(g?.name ?: "")
            hint = "Guruh nomi"
            setSelection(text.length)
        }
        val pad = (16 * resources.displayMetrics.density).toInt()
        val box = FrameLayout(ctx).apply { setPadding(pad, pad / 2, pad, 0); addView(input) }
        MaterialAlertDialogBuilder(ctx)
            .setTitle(if (g == null) "Yangi guruh" else "Nomini tahrirlash")
            .setView(box)
            .setPositiveButton("Saqlash") { _, _ ->
                val name = input.text?.toString()?.trim().orEmpty()
                if (name.isEmpty()) {
                    Toast.makeText(ctx, "Guruh nomini kiriting", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                lifecycleScope.launch {
                    try {
                        val repo = ctx.app().repo
                        if (g == null) repo.addGroup(name) else repo.renameGroup(g.uid, name)
                        reload()
                    } catch (e: Exception) {
                        Toast.makeText(ctx, "Xato: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
            .setNegativeButton("Bekor", null)
            .show()
    }

    private fun showMembers(groupUid: String) {
        val ctx = requireContext()
        lifecycleScope.launch {
            val repo = ctx.app().repo
            val members = repo.groupMembers(groupUid)
            val students = members.mapNotNull { m ->
                repo.students().find { it.uid == m.studentUid }?.let { Triple(m.uid, it.full_name, it.phone) }
            }
            if (students.isEmpty()) {
                val options = arrayOf("➕ O'quvchi qo'shish")
                MaterialAlertDialogBuilder(ctx)
                    .setTitle("Guruh a'zolari")
                    .setItems(options) { _, _ -> pickStudent(groupUid) }
                    .setNegativeButton("Yopish", null)
                    .show()
                return@launch
            }
            val labels = students.map { "${it.second} • ${it.third.ifEmpty { "—" }}" }
                .plus("➕ O'quvchi qo'shish").toTypedArray()
            MaterialAlertDialogBuilder(ctx)
                .setTitle("Guruh a'zolari")
                .setItems(labels) { _, which ->
                    if (which == students.size) {
                        pickStudent(groupUid)
                    } else {
                        val memberUid = students[which].first
                        confirm(ctx, "Bu o'quvchini guruhdan chiqarishmi?") {
                            lifecycleScope.launch {
                                repo.removeGroupMember(memberUid)
                                showMembers(groupUid)
                                reload()
                            }
                        }
                    }
                }
                .setNegativeButton("Yopish", null)
                .show()
        }
    }

    private fun pickStudent(groupUid: String) {
        val ctx = requireContext()
        lifecycleScope.launch {
            val repo = ctx.app().repo
            val avail = repo.studentsNotInGroup(groupUid)
            if (avail.isEmpty()) {
                Toast.makeText(ctx, "Qo'shishga o'quvchi yo'q", Toast.LENGTH_SHORT).show()
                return@launch
            }
            val labels = avail.map { "${it.full_name} • ${it.phone.ifEmpty { "—" }}" }.toTypedArray()
            MaterialAlertDialogBuilder(ctx)
                .setTitle("O'quvchini tanlang")
                .setItems(labels) { _, which ->
                    lifecycleScope.launch {
                        repo.addGroupMember(groupUid, avail[which].uid)
                        showMembers(groupUid)
                        reload()
                    }
                }
                .setNegativeButton("Bekor", null)
                .show()
        }
    }
}
