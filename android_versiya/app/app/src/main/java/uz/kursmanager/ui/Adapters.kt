package uz.kursmanager.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import uz.kursmanager.R

/** Umumiy qator: avatar + sarlavha + tag + badge + ⋮ menyu. */
class RowAdapter(
    private var items: List<RowData>,
    private val onMenu: (RowData, String) -> Unit
) : RecyclerView.Adapter<RowAdapter.H>() {

    data class RowData(
        val key: String,
        val title: String,
        val sub: String,
        val badgeText: String = "",
        val badgeColor: String = "#93A1BD",
        val menu: List<Pair<String, String>> = emptyList()
    )

    class H(v: View) : RecyclerView.ViewHolder(v) {
        val avatar: TextView = v.findViewById(R.id.avatar)
        val title: TextView = v.findViewById(R.id.title)
        val sub: TextView = v.findViewById(R.id.sub)
        val badgeSlot: LinearLayout = v.findViewById(R.id.badgeSlot)
        val more: ImageButton = v.findViewById(R.id.btnMore)
    }

    override fun onCreateViewHolder(p: ViewGroup, t: Int): H {
        val v = LayoutInflater.from(p.context).inflate(R.layout.item_row, p, false)
        return H(v)
    }

    override fun getItemCount() = items.size

    override fun onBindViewHolder(h: H, pos: Int) {
        val it = items[pos]
        h.avatar.text = initialsOf(it.title)
        h.title.text = it.title
        h.sub.text = it.sub
        h.sub.visibility = if (it.sub.isEmpty()) View.GONE else View.VISIBLE
        h.badgeSlot.removeAllViews()
        if (it.badgeText.isNotEmpty()) h.badgeSlot.addView(statusBadge(h.itemView.context, it.badgeText, it.badgeColor))
        if (it.menu.isEmpty()) {
            h.more.visibility = View.GONE
        } else {
            h.more.visibility = View.VISIBLE
            h.more.setOnClickListener { v ->
                val pm = PopupMenu(v.context, v)
                it.menu.forEachIndexed { i, m -> pm.menu.add(0, i, i, m.second) }
                pm.setOnMenuItemClickListener { mi ->
                    onMenu(it, it.menu[mi.itemId].first)
                    true
                }
                pm.show()
            }
        }
    }

    fun setData(d: List<RowData>) {
        items = d
        notifyDataSetChanged()
    }
}

/** Qator menyusi: Batafsil/Tahrirlash + statuslar + O'chirish (o'quvchi uchun). */
fun studentMenu(current: String): List<Pair<String, String>> {
    val m = mutableListOf("detail" to "Batafsil", "edit" to "Tahrirlash")
    if (current != "paid") m.add("status:paid" to "● To'lov qilingan")
    if (current != "pending") m.add("status:pending" to "● Kutilmoqda")
    if (current != "unpaid") m.add("status:unpaid" to "● To'lov qilinmagan")
    m.add("delete" to "O'chirish")
    return m
}

/** Sodda menyu: Tahrirlash + O'chirish. */
fun simpleMenu(): List<Pair<String, String>> =
    listOf("edit" to "Tahrirlash", "delete" to "O'chirish")

typealias StudentAdapter = RowAdapter
