package uz.kursmanager.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app

class ReportsFragment : Fragment() {
    override fun onCreateView(inf: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        val v = inf.inflate(R.layout.fragment_dashboard, c, false)
        val grid = v.findViewById<android.widget.GridLayout>(R.id.stats)
        val list = v.findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.recent)
        list.visibility = View.GONE
        lifecycleScope.launch {
            val repo = requireContext().app().repo
            val total = repo.studentCount()
            val paid = repo.countByStatus("paid")
            val pending = repo.countByStatus("pending")
            val unpaid = repo.countByStatus("unpaid")
            val revenue = repo.revenue()
            grid.removeAllViews()
            grid.addView(statCard("Jami o'quvchilar", "$total", "#2B7FFF"))
            grid.addView(statCard("To'lov qilganlar", "$paid", "#22C55E"))
            grid.addView(statCard("Jami tushum", "%,.0f so'm".format(revenue).replace(",", " "), "#22C55E"))
            grid.addView(statCard("Kutilmoqda", "$pending", "#F5A80B"))
            grid.addView(statCard("To'lov qilmaganlar", "$unpaid", "#F0435A"))
        }
        return v
    }

    private fun statCard(label: String, value: String, color: String): View {
        val ctx = requireContext()
        val box = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            val p = (12 * resources.displayMetrics.density).toInt()
            setPadding(p, p, p, p)
            background = android.graphics.drawable.GradientDrawable().apply {
                shape = android.graphics.drawable.GradientDrawable.RECTANGLE
                cornerRadius = 28f
                setColor(android.graphics.Color.parseColor("#0E1628"))
                setStroke(2, android.graphics.Color.parseColor(color))
            }
        }
        val lp = android.widget.GridLayout.LayoutParams().apply {
            width = 0
            columnSpec = android.widget.GridLayout.spec(android.widget.GridLayout.UNDEFINED, 1f)
            setMargins(8, 8, 8, 8)
        }
        box.layoutParams = lp
        val t1 = TextView(ctx).apply { text = label; setTextColor(android.graphics.Color.parseColor("#93A1BD")); textSize = 12f }
        val t2 = TextView(ctx).apply {
            text = value; textSize = 22f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(android.graphics.Color.parseColor(color))
        }
        box.addView(t1); box.addView(t2)
        return box
    }
}
