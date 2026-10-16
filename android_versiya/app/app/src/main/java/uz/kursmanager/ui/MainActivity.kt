package uz.kursmanager.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.view.MenuItem
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.GravityCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.kursmanager.BuildConfig
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.databinding.ActivityMainBinding
import uz.kursmanager.sync.SyncWorker
import uz.kursmanager.update.UpdateChecker
import uz.kursmanager.update.UpdateInfo

class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        // Sarlavhadagi versiya chip'i (header layout kechikta inflate qilinishi
        // mumkin, shuning uchun layout pass'dan keyin o'rnatamiz)
        b.nav.post { applyHeaderVersion() }

        b.btnMenu.setOnClickListener {
            b.drawer.openDrawer(GravityCompat.START)
            b.nav.post { applyHeaderVersion() }
            refreshUpdateIndicator()
        }
        b.btnSync.setOnClickListener { onSyncClicked() }

        b.nav.setNavigationItemSelectedListener { item: MenuItem ->
            b.drawer.closeDrawers()
            when (item.itemId) {
                R.id.nav_dashboard -> open(DashboardFragment(), "Bosh sahifa")
                R.id.nav_students -> open(StudentsFragment(), "O'quvchilar")
                R.id.nav_groups -> open(GroupsFragment(), "Guruhlar")
                R.id.nav_payments -> open(PaymentsFragment(), "To'lovlar")
                R.id.nav_tests -> open(TestsFragment(), "Test natijalari")
                R.id.nav_attendance -> open(AttendanceFragment(), "Davomat")
                R.id.nav_reminders -> open(RemindersFragment(), "Eslatmalar")
                R.id.nav_reports -> open(ReportsFragment(), "Hisobotlar")
                R.id.nav_update -> onUpdateMenuClicked()
                R.id.nav_pairing -> startActivity(Intent(this, PairingActivity::class.java))
                R.id.nav_sync -> onSyncClicked()
            }
            if (item.isCheckable) item.isChecked = true
            refreshUpdateIndicator()
            true
        }

        SyncWorker.schedulePeriodic(this)
        // Ilova ochilganda avtomatik sinxron (juftlangan bo'lsa)
        lifecycleScope.launch {
            try {
                if (app().sync.isPaired) {
                    val r = app().sync.fullSync()
                    r.onSuccess { open(DashboardFragment(), "Bosh sahifa") }
                    r.onFailure { open(DashboardFragment(), "Bosh sahifa") }
                } else open(DashboardFragment(), "Bosh sahifa")
            } catch (e: Exception) {
                open(DashboardFragment(), "Bosh sahifa")
            }
        }

        // Yangi versiyani tekshirish
        checkForUpdate()

        // Android 13+ bildirishnoma ruxsatini so'rash
        requestNotificationPermission()
    }

    private var cachedUpdateInfo: UpdateInfo? = null

    private fun applyHeaderVersion() {
        val tv = b.nav.findViewById<TextView>(R.id.tvHeaderVersion) ?: return
        tv.text = "v${BuildConfig.VERSION_NAME}"
    }

    private fun checkForUpdate() {
        lifecycleScope.launch {
            val info = UpdateChecker.checkForUpdate()
            cachedUpdateInfo = info
            // Indikator: yangilanish bor bo'lsa ko'k yonadi, aks holda o'chiq (default)
            applyUpdateIndicator(info != null)
            if (info != null) showUpdateDialog(info)
        }
    }

    private fun applyUpdateIndicator(hasUpdate: Boolean) {
        val item = b.nav.menu.findItem(R.id.nav_update) ?: return
        val base = getString(R.string.menu_update)
        if (!hasUpdate) {
            item.title = base
            item.icon?.setTint(ContextCompat.getColor(this, R.color.text_dim))
            return
        }
        val text = "$base  •"
        val span = SpannableString(text)
        val blue = ContextCompat.getColor(this, R.color.primary)
        span.setSpan(ForegroundColorSpan(blue), 0, text.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        span.setSpan(StyleSpan(Typeface.BOLD), 0, text.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        item.title = span
        item.icon = item.icon?.mutate()?.also { it.setTint(blue) }
    }

    // Menyu ochilganda indikatorni yangilash (dialogsiz)
    private fun refreshUpdateIndicator() {
        applyUpdateIndicator(cachedUpdateInfo != null)
        if (cachedUpdateInfo != null) return
        lifecycleScope.launch {
            val info = UpdateChecker.checkForUpdate()
            if (info != null) {
                cachedUpdateInfo = info
                applyUpdateIndicator(true)
            }
        }
    }

    private fun onUpdateMenuClicked() {
        val info = cachedUpdateInfo
        if (info != null) {
            showUpdateDialog(info)
        } else {
            Toast.makeText(
                this,
                "Sizda eng so'nggi versiya (v${BuildConfig.VERSION_NAME}) o'rnatilgan.\n\nYangilanishlar mavjud emas.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    private fun showUpdateDialog(info: UpdateInfo) {
        AlertDialog.Builder(this@MainActivity)
            .setTitle("🔵 Yangilanish mavjud!")
            .setMessage("Versiya: ${info.version}\n\n${info.notes}\n\nHozir yuklab o'rnatilsinmi?")
            .setPositiveButton("Ha, yangilash") { _, _ ->
                lifecycleScope.launch {
                    Toast.makeText(this@MainActivity, "Yuklanmoqda...", Toast.LENGTH_SHORT).show()
                    val ok = UpdateChecker.downloadAndInstall(this@MainActivity, info) { progress ->
                        // Progress callback
                    }
                    if (!ok) {
                        Toast.makeText(this@MainActivity, "Yuklab bo'lmadi. Internetni tekshiring.", Toast.LENGTH_LONG).show()
                    }
                }
            }
            .setNegativeButton("Keyinroq", null)
            .show()
    }

    private fun open(f: Fragment, title: String) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.content, f).commit()
        b.tvTitle.text = title
        val id = when (title) {
            "Bosh sahifa" -> R.id.nav_dashboard
            "O'quvchilar" -> R.id.nav_students
            "Guruhlar" -> R.id.nav_groups
            "To'lovlar" -> R.id.nav_payments
            "Test natijalari" -> R.id.nav_tests
            "Davomat" -> R.id.nav_attendance
            "Eslatmalar" -> R.id.nav_reminders
            "Hisobotlar" -> R.id.nav_reports
            else -> 0
        }
        if (id != 0) b.nav.setCheckedItem(id)
    }

    private fun onSyncClicked() {
        lifecycleScope.launch {
            Toast.makeText(this@MainActivity, "Sinxronlanmoqda...", Toast.LENGTH_SHORT).show()
            try {
                val r = app().sync.fullSync()
                r.onSuccess {
                    Toast.makeText(this@MainActivity,
                        "Tayyor: olindi ${it.pulled}, yuborildi ${it.pushed}",
                        Toast.LENGTH_LONG).show()
                    recreate()
                }
                r.onFailure {
                    Toast.makeText(this@MainActivity,
                        "Xato: ${it.message ?: "ulanib bo'lmadi"}. Avval kompyuterga ulaning.",
                        Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Xato: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 101)
            }
        }
    }
}
