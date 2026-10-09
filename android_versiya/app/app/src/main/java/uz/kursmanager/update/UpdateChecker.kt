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
import java.util.concurrent.TimeUnit

data class UpdateInfo(
    val version: String,
    val versionCode: Int,
    val url: String,
    val notes: String
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
                val json = JSONObject(body)
                val android = json.optJSONObject("android") ?: return@withContext null

                val remoteCode = android.optInt("versionCode", 0)
                val remoteVersion = android.optString("version", "")
                val url = android.optString("url", "")
                val notes = android.optString("notes", "")

                if (remoteCode > BuildConfig.VERSION_CODE && url.isNotEmpty()) {
                    UpdateInfo(remoteVersion, remoteCode, url, notes)
                } else {
                    null
                }
            }
        } catch (_: Exception) {
            null
        }
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

    private fun installApk(context: Context, apkFile: File) {
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
