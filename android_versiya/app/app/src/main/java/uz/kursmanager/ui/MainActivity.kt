package uz.kursmanager.ui

import android.content.Intent
import android.os.Bundle
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.kursmanager.R
import uz.kursmanager.app
import uz.kursmanager.databinding.ActivityMainBinding
import uz.kursmanager.sync.SyncWorker
import uz.kursmanager.update.UpdateChecker

class MainActivity : AppCompatActivity() {

    private lateinit var b: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        b.btnMenu.setOnClickListener { b.drawer.openDrawer(GravityCompat.START) }
        b.btnSync.setOnClickListener { onSyncClicked() }

        b.nav.setNavigationItemSelectedListener { item: MenuItem ->
            b.drawer.closeDrawers()
            when (item.itemId) {
                R.id.nav_dashboard -> open(DashboardFragment(), "Bosh sahifa")
                R.id.nav_students -> open(StudentsFragment(), "O'quvchilar")
                R.id.nav_payments -> open(PaymentsFragment(), "To'lovlar")
                R.id.nav_tests -> open(TestsFragment(), "Test natijalari")
                R.id.nav_attendance -> open(AttendanceFragment(), "Davomat")
                R.id.nav_reminders -> open(RemindersFragment(), "Eslatmalar")
                R.id.nav_reports -> open(ReportsFragment(), "Hisobotlar")
                R.id.nav_pairing -> startActivity(Intent(this, PairingActivity::class.java))
                R.id.nav_sync -> onSyncClicked()
            }
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
    }

    private fun checkForUpdate() {
        lifecycleScope.launch {
            val info = UpdateChecker.checkForUpdate() ?: return@launch
            AlertDialog.Builder(this@MainActivity)
                .setTitle("Yangi versiya mavjud!")
                .setMessage("Versiya: ${info.version}\n\n${info.notes}\n\nHozir yuklab o'rnatilsinmi?")
                .setPositiveButton("Ha, yangilash") { _, _ ->
                    lifecycleScope.launch {
                        Toast.makeText(this@MainActivity, "Yuklanmoqda...", Toast.LENGTH_SHORT).show()
                        val ok = UpdateChecker.downloadAndInstall(this@MainActivity, info) { progress ->
                            // Progress bar qo'shish mumkin
                        }
                        if (!ok) {
                            Toast.makeText(this@MainActivity, "Yuklab bo'lmadi. Internetni tekshiring.", Toast.LENGTH_LONG).show()
                        }
                    }
                }
                .setNegativeButton("Keyinroq", null)
                .show()
        }
    }

    private fun open(f: Fragment, title: String) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.content, f).commit()
        b.tvTitle.text = title
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
}
