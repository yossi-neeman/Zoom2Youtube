package com.neeman.zoom2youtube.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class Prefs(context: Context) {
    data class Credentials(val serverUrl: String, val username: String, val password: String)

    private val plain: SharedPreferences = context.getSharedPreferences("z2y", Context.MODE_PRIVATE)

    // The password is kept so the app can silently sign in again when the 24h server session expires.
    // If the Keystore is unavailable we simply don't remember it.
    private val secure: SharedPreferences? = try {
        val key = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            context, "z2y_secure", key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    } catch (e: Exception) {
        null
    }

    var serverUrl: String
        get() = plain.getString("server", DEFAULT_SERVER) ?: DEFAULT_SERVER
        set(v) = plain.edit().putString("server", v).apply()

    var username: String
        get() = plain.getString("username", "") ?: ""
        set(v) = plain.edit().putString("username", v).apply()

    val credentials: Credentials?
        get() {
            val password = secure?.getString("password", null) ?: return null
            val user = username.ifEmpty { return null }
            return Credentials(serverUrl, user, password)
        }

    fun saveCredentials(c: Credentials) {
        serverUrl = c.serverUrl
        username = c.username
        secure?.edit()?.putString("password", c.password)?.apply()
    }

    fun forgetPassword() {
        secure?.edit()?.remove("password")?.apply()
    }

    /** "password" (stored credentials re-login silently) or "google" (only the session cookie). */
    var authMode: String
        get() = plain.getString("authMode", MODE_PASSWORD) ?: MODE_PASSWORD
        set(v) = plain.edit().putString("authMode", v).apply()

    /** Serialized session cookies, so a Google sign-in survives app restarts (until the 24h session lapses). */
    var cookies: String?
        get() = secure?.getString("cookies", null)
        set(v) {
            secure?.edit()?.apply { if (v == null) remove("cookies") else putString("cookies", v) }?.apply()
        }

    /** Forget everything that proves who is signed in. */
    fun signOut() {
        forgetPassword()
        cookies = null
        authMode = MODE_PASSWORD
    }

    var days: Int
        get() = plain.getInt("days", 5)
        set(v) = plain.edit().putInt("days", v).apply()

    var lastMasechet: String
        get() = plain.getString("lastMasechet", "") ?: ""
        set(v) = plain.edit().putString("lastMasechet", v).apply()

    var lastDaf: String
        get() = plain.getString("lastDaf", "") ?: ""
        set(v) = plain.edit().putString("lastDaf", v).apply()

    var lastPlaylistId: String
        get() = plain.getString("lastPlaylistId", "") ?: ""
        set(v) = plain.edit().putString("lastPlaylistId", v).apply()

    companion object {
        const val DEFAULT_SERVER = "https://z2y.neemanet.com"
        const val MODE_PASSWORD = "password"
        const val MODE_GOOGLE = "google"
    }
}
