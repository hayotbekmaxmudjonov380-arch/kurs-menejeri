package uz.kursmanager.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import kotlinx.coroutines.launch
import uz.kursmanager.app
import uz.kursmanager.databinding.ActivityPairingBinding
import uz.kursmanager.sync.SyncWorker

class PairingActivity : AppCompatActivity() {

    private lateinit var b: ActivityPairingBinding

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startQrScan()
        else Toast.makeText(this, "Kamera ruxsati kerak", Toast.LENGTH_SHORT).show()
    }

    private val qrScanLauncher = registerForActivityResult(ScanContract()) { result ->
        if (result.contents != null) {
            parseQrAndConnect(result.contents)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityPairingBinding.inflate(layoutInflater)
        setContentView(b.root)
        supportActionBar?.title = "Kompyuterga ulash"

        b.btnBack.setOnClickListener { finish() }

        if (app().sync.isPaired) {
            setStatus("Hozir ulangan: ${app().sync.serverUrl}")
        }

        b.btnScanQr.setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                startQrScan()
            } else {
                cameraPermission.launch(Manifest.permission.CAMERA)
            }
        }

        b.btnPair.setOnClickListener {
            val ip = b.inIp.text.toString().trim()
            val code = b.inCode.text.toString().trim()
            b.ipLayout.error = null
            b.codeLayout.error = null
            if (ip.isEmpty()) {
                b.ipLayout.error = "IP manzilni kiriting"
                return@setOnClickListener
            }
            if (code.length != 4) {
                b.codeLayout.error = "4 xonali kod kiriting"
                return@setOnClickListener
            }
            connectTo(ip, code)
        }
    }

    private fun startQrScan() {
        val options = ScanOptions()
        options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
        options.setPrompt("Kompyuterdagi QR kodni skanerlang")
        options.setBeepEnabled(true)
        options.setOrientationLocked(true)
        qrScanLauncher.launch(options)
    }

    private fun parseQrAndConnect(contents: String) {
        // Format: KM|IP:PORT|KOD
        val parts = contents.split("|")
        if (parts.size >= 3 && parts[0] == "KM") {
            val ipPort = parts[1]
            val code = parts[2]
            val ip = ipPort.substringBefore(":")
            b.inIp.setText(ip)
            b.inCode.setText(code)
            connectTo(ip, code)
        } else {
            setStatus("Noto'g'ri QR kod. Kompyuterdagi «Telefon ulash» oynasidan QR oling.")
        }
    }

    private fun connectTo(ip: String, code: String) {
        app().sync.serverUrl = "http://$ip:8741"
        setStatus("Tekshirilmoqda...")
        b.btnPair.isEnabled = false
        b.btnScanQr.isEnabled = false
        lifecycleScope.launch {
            try {
                val v = app().sync.hello().getOrThrow()
                setStatus("Kompyuter topildi (v$v). Ulanmoqda...")
                val name = android.os.Build.MODEL ?: "Android"
                app().sync.pair(code, name).getOrThrow()
                setStatus("Ulandi! Sinxronlanmoqda...")
                val r = app().sync.fullSync().getOrThrow()
                setStatus("Tayyor! Olindi: ${r.pulled}, yuborildi: ${r.pushed}")
                // Avtomatik fon sinxronlashishni yoqish
                SyncWorker.schedulePeriodic(this@PairingActivity)
                Toast.makeText(this@PairingActivity, "Kompyuterga ulandi!", Toast.LENGTH_LONG).show()
                finish()
            } catch (e: Exception) {
                setStatus("Xato: ${e.message}")
            } finally {
                b.btnPair.isEnabled = true
                b.btnScanQr.isEnabled = true
            }
        }
    }

    private fun setStatus(t: String) {
        b.tvStatus.text = t
        b.tvStatus.visibility = android.view.View.VISIBLE
    }
}
