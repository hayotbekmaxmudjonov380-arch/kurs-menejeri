package uz.kursmanager.net

import com.google.gson.annotations.SerializedName
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

// ---- DTO ----

data class HelloResp(
    val app: String = "",
    val version: String = "",
    val sync: Int = 0,
    @SerializedName("needs_pairing") val needsPairing: Boolean = true,
    @SerializedName("server_time") val serverTime: String = ""
)

data class PairReq(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("device_name") val deviceName: String,
    val code: String
)

data class PairResp(val ok: Boolean = false, val token: String = "", val error: String = "")

data class ChangeItem(
    val table: String = "",
    val uid: String = "",
    @SerializedName("updated_at") val updatedAt: String = "",
    val deleted: Boolean = false,
    val row: Map<String, Any?> = emptyMap()
)

data class ChangesResp(
    val changes: List<ChangeItem> = emptyList(),
    val deleted: List<Map<String, Any?>> = emptyList()
)

data class PushReq(
    @SerializedName("device_id") val deviceId: String,
    val changes: List<ChangeItem>,
    val deleted: List<Map<String, String>> = emptyList()
)

data class PushResp(val applied: Int = 0, val skipped: Int = 0, val conflicts: Int = 0, val deleted: Int = 0)

// ---- API ----

interface SyncApi {
    @GET("sync/hello")
    suspend fun hello(): HelloResp

    @POST("sync/pair")
    suspend fun pair(@Body req: PairReq): PairResp

    @GET("sync/changes")
    suspend fun changes(
        @Header("X-Device-Token") token: String,
        @Query("since") since: String,
        @Query("device_id") deviceId: String
    ): ChangesResp

    @POST("sync/push")
    suspend fun push(
        @Header("X-Device-Token") token: String,
        @Body req: PushReq
    ): PushResp
}

object ApiFactory {
    fun create(baseUrl: String): SyncApi {
        val url = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
        return Retrofit.Builder()
            .baseUrl(url)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SyncApi::class.java)
    }
}
