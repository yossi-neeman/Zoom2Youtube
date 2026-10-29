package com.neeman.zoom2youtube.data

import android.util.Base64
import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/** Talks to the Flask backend (cookie session + JSON endpoints). */
class ApiClient(private val prefs: Prefs) {

    private val http = OkHttpClient.Builder()
        .cookieJar(PersistentCookieJar(prefs))
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    // The login endpoint answers success with a redirect; we want to see it, not follow it.
    private val loginHttp = http.newBuilder().followRedirects(false).followSslRedirects(false).build()

    private val loginMutex = Mutex()

    @Volatile
    private var baseUrl: String = ""

    suspend fun login(serverUrl: String, username: String, password: String) {
        val url = normalizeUrl(serverUrl)
        val request = try {
            Request.Builder().url("$url/login")
                .post(FormBody.Builder().add("username", username).add("password", password).build())
                .build()
        } catch (e: IllegalArgumentException) {
            throw ApiException("Invalid server URL")
        }
        val code = try {
            loginHttp.newCall(request).await().use { it.code }
        } catch (e: IOException) {
            throw ApiException("Can't reach the server: ${e.message}", retryable = true)
        }
        when (code) {
            301, 302, 303, 307, 308 -> baseUrl = url
            429 -> throw ApiException("Too many failed attempts. Try again in a few minutes.", code)
            403 -> throw ApiException("Password sign-in is disabled on this server.", code)
            200 -> throw ApiException("Invalid username or password.", code)
            else -> throw ApiException("Unexpected server response (HTTP $code).", code)
        }
    }

    /** URL to open in the system browser; it ends in a `z2y://login?code=...` redirect back to the app. */
    fun googleLoginUrl(serverUrl: String) = "${normalizeUrl(serverUrl)}/auth/google?app=1"

    /** Trade the one-time code from the redirect for a session cookie; returns the signed-in email. */
    suspend fun exchangeAppCode(serverUrl: String, code: String): String {
        baseUrl = normalizeUrl(serverUrl)
        try {
            return json("/auth/app-exchange", JSONObject().put("code", code), allowRelogin = false).optString("username")
        } catch (e: ApiException) {
            baseUrl = ""
            throw e
        }
    }

    /** Reuse a session cookie saved by an earlier run; the first API call tells if it's still valid. */
    fun resumeSession(serverUrl: String) {
        baseUrl = normalizeUrl(serverUrl)
    }

    suspend fun recordings(days: Int): List<Recording> {
        val arr = json("/api/recordings?days=$days").getJSONArray("recordings")
        return (0 until arr.length()).map {
            val o = arr.getJSONObject(it)
            Recording(
                id = o.getString("id"),
                topic = o.optString("topic", ""),
                startTime = o.optString("start_time", ""),
                durationMin = o.optInt("duration", 0),
            )
        }
    }

    suspend fun playlists(): List<Playlist> {
        val arr = json("/api/playlists").getJSONArray("playlists")
        return (0 until arr.length()).map {
            val o = arr.getJSONObject(it)
            Playlist(o.getString("id"), o.optString("title", ""), o.optInt("item_count", 0))
        }
    }

    /** Returns the JPEG bytes of the generated thumbnail. */
    suspend fun thumbnailPreview(text: String): ByteArray {
        val dataUri = json("/api/thumbnail/preview", JSONObject().put("text", text)).getString("preview_data")
        return Base64.decode(dataUri.substringAfter("base64,"), Base64.DEFAULT)
    }

    /**
     * Download from Zoom and upload to YouTube in one go. The server runs it as a background job, so
     * a dropped connection doesn't stop it: we poll until it finishes. Asking again is always safe -
     * the server starts at most one job per recording and hands back the existing one.
     */
    suspend fun publish(
        masechet: String,
        daf: String,
        playlistId: String?,
        recordingId: String,
        description: String,
        privacy: String,
        onStatus: (String) -> Unit,
    ): UploadResult {
        val body = JSONObject()
            .put("masechet", masechet)
            .put("daf", daf)
            .put("recording_id", recordingId)
            .put("description", description)
            .put("privacy", privacy)
        if (!playlistId.isNullOrEmpty()) body.put("playlist_id", playlistId)

        val deadline = System.currentTimeMillis() + PUBLISH_DEADLINE_MS
        var job = retrying(deadline) { json("/api/publish", body).getJSONObject("job") }
        while (true) {
            when (job.getString("status")) {
                "succeeded" -> return UploadResult(job.getString("video_id"), job.getString("video_url"))
                "failed" -> throw ApiException(job.optString("error").ifEmpty { "Publishing failed" })
            }
            onStatus(job.getString("status"))
            delay(POLL_DELAY_MS)
            val id = job.getString("id")
            job = retrying(deadline) { json("/api/publish/$id").getJSONObject("job") }
        }
    }

    /** Repeats [block] while it fails with a transient error (proxy timeout, dropped connection). */
    private suspend fun <T> retrying(deadline: Long, block: suspend () -> T): T {
        while (true) {
            try {
                return block()
            } catch (e: ApiException) {
                if (!e.retryable || System.currentTimeMillis() > deadline) throw e
                delay(RETRY_DELAY_MS)
            }
        }
    }

    // ---- plumbing ----

    private suspend fun json(
        path: String,
        body: JSONObject? = null,
        allowRelogin: Boolean = true,
    ): JSONObject {
        if (baseUrl.isEmpty()) throw ApiException("Not signed in", 401)
        val builder = Request.Builder().url(baseUrl + path)
        if (body != null) {
            builder.post(body.toString().toRequestBody("application/json; charset=utf-8".toMediaType()))
        }

        val (code, text) = try {
            http.newCall(builder.build()).await().use {
                it.code to it.body?.string().orEmpty()
            }
        } catch (e: IOException) {
            throw ApiException(
                if (e is java.net.SocketTimeoutException) "The request timed out" else "Network error: ${e.message}",
                retryable = true,
            )
        }

        if (code == 401 && allowRelogin) {
            relogin()
            return json(path, body, allowRelogin = false)
        }

        val transient = code in TRANSIENT_CODES
        val obj = try {
            JSONObject(text)
        } catch (e: JSONException) {
            throw ApiException("Server error (HTTP $code)", code, retryable = transient)
        }
        if (code !in 200..299 || !obj.optBoolean("success", false)) {
            throw ApiException(obj.optString("error").ifEmpty { "HTTP $code" }, code, retryable = transient)
        }
        return obj
    }

    /** The server session lasts 24h; sign in again with the stored credentials when it lapses. */
    private suspend fun relogin() = loginMutex.withLock {
        val c = prefs.credentials ?: throw ApiException("Session expired - please sign in again.", 401)
        login(c.serverUrl, c.username, c.password)
    }

    companion object {
        private val TRANSIENT_CODES = setOf(408, 502, 503, 504, 520, 522, 524)
        private const val PUBLISH_DEADLINE_MS = 2L * 60 * 60 * 1000
        private const val POLL_DELAY_MS = 3_000L
        private const val RETRY_DELAY_MS = 3_000L

        fun normalizeUrl(input: String): String {
            val trimmed = input.trim().trimEnd('/')
            return if (trimmed.contains("://")) trimmed else "https://$trimmed"
        }
    }
}

private suspend fun Call.await(): Response = suspendCancellableCoroutine { cont ->
    cont.invokeOnCancellation { cancel() }
    enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            if (cont.isActive) cont.resumeWithException(e)
        }

        override fun onResponse(call: Call, response: Response) {
            cont.resume(response)
        }
    })
}

/**
 * Keeps the session cookie for the app's lifetime and mirrors it into [Prefs] so a Google sign-in
 * (which has no stored password to fall back on) survives a restart.
 */
private class PersistentCookieJar(private val prefs: Prefs) : CookieJar {
    private val store = ConcurrentHashMap<String, List<Cookie>>()

    init {
        // One line per cookie: "<host>\t<Set-Cookie style text>".
        prefs.cookies?.lineSequence()?.forEach { line ->
            val host = line.substringBefore('\t', "")
            val text = line.substringAfter('\t', "")
            if (host.isEmpty() || text.isEmpty()) return@forEach
            val url = HttpUrl.Builder().scheme("https").host(host).build()
            Cookie.parse(url, text)?.let { store[host] = store[host].orEmpty() + it }
        }
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val kept = store[url.host].orEmpty().filter { old -> cookies.none { it.name == old.name } }
        store[url.host] = kept + cookies
        persist()
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val now = System.currentTimeMillis()
        return store[url.host].orEmpty().filter { it.expiresAt > now && it.matches(url) }
    }

    private fun persist() {
        val now = System.currentTimeMillis()
        prefs.cookies = store.entries
            .flatMap { (host, list) -> list.filter { it.persistent && it.expiresAt > now }.map { "$host\t$it" } }
            .joinToString("\n")
            .ifEmpty { null }
    }
}
