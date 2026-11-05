package uz.kursmanager.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.widget.Toast
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import uz.kursmanager.BuildConfig
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

data class UpdateInfo(
    val version: String,
    val versionCode: Int,
    val url: String,
    val notes: String,
    val sha256: String = "",
    val minVersion: String = ""
)

object UpdateChecker {

    private const val UPDATE_URL =
        "https://raw.githubusercontent.com/hayotbekmaxmudjonov380-arch/kurs-menejeri/main/updates.json"

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun checkForUpdate(): UpdateInfo? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(UPDATE_URL)
                .header("User-Agent", "KursManager-Android")
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@withContext null
                val body = response.body?.string() ?: return@withContext null
                // UTF-8 BOM JSONTokener uchun oqilmagan belgi — olib tashlaymiz
                val json = JSONObject(body.removePrefix("\uFEFF"))
                val android = json.optJSONObject("android") ?: return@withContext null

                val remoteCode = android.optInt("versionCode", 0)
                val remoteVersion = android.optString("version", "")
                val url = android.optString("url", "")
                val notes = android.optString("notes", "")
                val sha256 = android.optString("sha256", "")
                val minVersion = android.optString("min_version", "")

                if (remoteCode > BuildConfig.VERSION_CODE && url.isNotEmpty()) {
                    UpdateInfo(remoteVersion, remoteCode, url, notes, sha256, minVersion)
                } else {
                    null
                }
            }
        } catch (_: Exception) {
            null
        }
    }

    /** Majburiy yangilanish: min_version joriy versiyadan baland bo'lsa. */
    fun isForced(info: UpdateInfo?): Boolean {
        val min = info?.minVersion?.trim().orEmpty()
        if (min.isEmpty()) return false
        return compareVersions(BuildConfig.VERSION_NAME, min) < 0
    }

    /** "1.3.17" kabi versiyalarni solishtiradi: -1 (a<b), 0, +1 (a>b). */
    private fun compareVersions(a: String, b: String): Int {
        val pa = a.split('.').map { it.filter(Char::isDigit).toIntOrNull() ?: 0 }
        val pb = b.split('.').map { it.filter(Char::isDigit).toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(pa.size, pb.size)) {
            val x = pa.getOrElse(i) { 0 }
            val y = pb.getOrElse(i) { 0 }
            if (x != y) return if (x < y) -1 else 1
        }
        return 0
    }

    suspend fun downloadAndInstall(context: Context, info: UpdateInfo, onProgress: (Int) -> Unit): Boolean =
        withContext(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url(info.url)
                    .header("User-Agent", "KursManager-Android")
                    .build()

                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) return@withContext false
                    val body = response.body ?: return@withContext false

                    val apkFile = File(context.cacheDir, "update_${info.version}.apk")
                    val total = body.contentLength()
                    var downloaded = 0L

                    apkFile.outputStream().use { out ->
                        body.byteStream().use { input ->
                            val buffer = ByteArray(8192)
                            var bytesRead: Int
                            while (input.read(buffer).also { bytesRead = it } != -1) {
                                out.write(buffer, 0, bytesRead)
                                downloaded += bytesRead
                                if (total > 0) {
                                    val progress = ((downloaded * 100) / total).toInt()
                                    withContext(Dispatchers.Main) { onProgress(progress) }
                                }
                            }
                        }
                    }

                    // Nayzat (sha256) tekshiruvi — fayl buzilgan bo'lsa o'rnatilmaydi
                    val actual = sha256Of(apkFile)
                    if (info.sha256.isNotBlank() &&
                        !actual.equals(info.sha256.trim(), ignoreCase = true)
                    ) {
                        apkFile.delete()
                        withContext(Dispatchers.Main) {
                            Toast.makeText(
                                context,
                                "Yuklangan fayl buzilgan (nazorat summasi mos emas). Qayta urinib ko'ring.",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                        return@withContext false
                    }

                    // O'rnatishni boshlash
                    withContext(Dispatchers.Main) {
                        installApk(context, apkFile)
                    }
                    true
                }
            } catch (_: Exception) {
                false
            }
        }

    /** Faylning sha256 nazorat summasi (16-lik, katta harflar bilan). */
    private fun sha256Of(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            var read: Int
            while (input.read(buffer).also { read = it } != -1) {
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02X".format(it) }
    }

    private fun installApk(context: Context, apkFile: File) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!context.packageManager.canRequestPackageInstalls()) {
                try {
                    val settingsIntent = Intent(
                        android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:${context.packageName}")
                    ).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(settingsIntent)
                    Toast.makeText(context, "Iltimos, ilovaga yangilanishni o'rnatish uchun ruxsat bering, so'ng qayta bosing.", Toast.LENGTH_LONG).show()
                    return
                } catch (_: Exception) {
                }
            }
        }

        val intent = Intent(Intent.ACTION_VIEW)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                apkFile
            )
            intent.setDataAndType(uri, "application/vnd.android.package-archive")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        } else {
            intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive")
        }

        try {
            context.startActivity(intent)
        } catch (_: Exception) {
            Toast.makeText(context, "O'rnatishda xatolik. Sozlamalardan 'Noma'lum manbalar' ni yoqing.", Toast.LENGTH_LONG).show()
        }
    }
}
