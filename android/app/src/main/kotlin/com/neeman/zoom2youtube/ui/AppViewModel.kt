package com.neeman.zoom2youtube.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.neeman.zoom2youtube.data.ApiClient
import com.neeman.zoom2youtube.data.ApiException
import com.neeman.zoom2youtube.data.Playlist
import com.neeman.zoom2youtube.data.Prefs
import com.neeman.zoom2youtube.data.Recording
import com.neeman.zoom2youtube.data.UploadResult
import com.neeman.zoom2youtube.data.thumbnailText
import com.neeman.zoom2youtube.data.videoTitle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class Screen { Booting, Login, Publish }

data class UiState(
    val screen: Screen = Screen.Booting,

    // login
    val serverUrl: String = "",
    val username: String = "",
    val loginBusy: Boolean = false,
    val loginError: String? = null,

    // publish form: recordings (the latest is pre-selected) ...
    val days: Int = 5,
    val recordings: List<Recording> = emptyList(),
    val recordingsLoading: Boolean = false,
    val recordingsError: String? = null,
    val selected: Recording? = null,

    // ... and what to publish it as
    val masechet: String = "",
    val daf: String = "",
    val description: String = "",
    val privacy: String = "public",
    val playlists: List<Playlist> = emptyList(),
    val playlistId: String = "",
    val thumbnailPreview: ByteArray? = null,
    val previewLoading: Boolean = false,
    val publishing: Boolean = false,
    val publishStatus: String = "",
    val publishResult: UploadResult? = null,

    /** One-shot message for a snackbar; cleared by [AppViewModel.messageShown]. */
    val message: String? = null,
) {
    val title get() = if (masechet.isNotBlank() && daf.isNotBlank()) videoTitle(masechet, daf.trim()) else ""
    val thumbText get() = if (masechet.isNotBlank() && daf.isNotBlank()) thumbnailText(masechet, daf.trim()) else ""
}

private val STATUS_TEXT = mapOf(
    "queued" to "Starting...",
    "downloading" to "Downloading from Zoom...",
    "uploading" to "Uploading to YouTube...",
)

class AppViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = Prefs(app)
    private val api = ApiClient(prefs)

    private val _state = MutableStateFlow(
        UiState(
            serverUrl = prefs.serverUrl,
            username = prefs.username,
            days = prefs.days,
            masechet = prefs.lastMasechet,
            daf = prefs.lastDaf,
        ),
    )
    val state: StateFlow<UiState> = _state.asStateFlow()

    init {
        val creds = prefs.credentials
        when {
            creds != null -> viewModelScope.launch {
                try {
                    api.login(creds.serverUrl, creds.username, creds.password)
                    enterPublish()
                } catch (e: ApiException) {
                    _state.update { it.copy(screen = Screen.Login, loginError = e.message) }
                }
            }
            prefs.authMode == Prefs.MODE_GOOGLE && prefs.cookies != null -> {
                // No password to fall back on: the saved session cookie either still works or we ask again.
                api.resumeSession(prefs.serverUrl)
                enterPublish()
            }
            else -> _state.update { it.copy(screen = Screen.Login) }
        }
    }

    // ---- login ----

    fun signIn(serverUrl: String, username: String, password: String) {
        if (_state.value.loginBusy) return
        _state.update { it.copy(loginBusy = true, loginError = null) }
        viewModelScope.launch {
            try {
                api.login(serverUrl, username, password)
                prefs.authMode = Prefs.MODE_PASSWORD
                prefs.saveCredentials(Prefs.Credentials(ApiClient.normalizeUrl(serverUrl), username, password))
                _state.update { it.copy(loginBusy = false, serverUrl = prefs.serverUrl, username = username) }
                enterPublish()
            } catch (e: ApiException) {
                _state.update { it.copy(loginBusy = false, loginError = e.message) }
            }
        }
    }

    /** Starts Google sign-in: remembers the server and returns the URL to open in the system browser. */
    fun googleSignInUrl(serverUrl: String): String {
        prefs.serverUrl = ApiClient.normalizeUrl(serverUrl)
        _state.update { it.copy(loginError = null, serverUrl = prefs.serverUrl) }
        return api.googleLoginUrl(serverUrl)
    }

    /** The browser redirected back with `z2y://login?code=...`. */
    fun completeGoogleSignIn(code: String) {
        _state.update { it.copy(loginBusy = true, loginError = null) }
        viewModelScope.launch {
            try {
                val email = api.exchangeAppCode(prefs.serverUrl, code)
                prefs.forgetPassword()
                prefs.authMode = Prefs.MODE_GOOGLE
                prefs.username = email
                _state.update { it.copy(loginBusy = false, username = email) }
                enterPublish()
            } catch (e: ApiException) {
                _state.update { it.copy(screen = Screen.Login, loginBusy = false, loginError = e.message) }
            }
        }
    }

    fun signOut() {
        prefs.signOut()
        _state.update {
            UiState(screen = Screen.Login, serverUrl = prefs.serverUrl, username = prefs.username, days = it.days)
        }
    }

    private fun enterPublish() {
        _state.update { it.copy(screen = Screen.Publish) }
        loadRecordings()
        loadPlaylists()
    }

    // ---- recordings ----

    fun setDays(days: Int) {
        prefs.days = days
        _state.update { it.copy(days = days) }
        loadRecordings()
    }

    fun loadRecordings() {
        val days = _state.value.days
        _state.update { it.copy(recordingsLoading = true, recordingsError = null) }
        viewModelScope.launch {
            try {
                val list = api.recordings(days).sortedByDescending { it.startTime }
                _state.update { s ->
                    s.copy(
                        recordings = list, recordingsLoading = false,
                        selected = s.selected?.takeIf { sel -> list.any { it.id == sel.id } } ?: list.firstOrNull(),
                    )
                }
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update { it.copy(recordingsLoading = false, recordingsError = e.message) }
            }
        }
    }

    fun select(recording: Recording) = _state.update { it.copy(selected = recording) }

    // ---- publish form ----

    fun setMasechet(v: String) {
        prefs.lastMasechet = v
        _state.update { it.copy(masechet = v, thumbnailPreview = null) }
    }

    fun setDaf(v: String) {
        prefs.lastDaf = v
        _state.update { it.copy(daf = v, thumbnailPreview = null) }
    }

    fun setDescription(v: String) = _state.update { it.copy(description = v) }

    fun setPrivacy(v: String) = _state.update { it.copy(privacy = v) }

    fun setPlaylist(id: String) {
        if (id.isNotEmpty()) prefs.lastPlaylistId = id
        _state.update { it.copy(playlistId = id) }
    }

    private fun loadPlaylists() {
        viewModelScope.launch {
            try {
                val list = api.playlists()
                // Same default as the web UI: last used, else the first playlist mentioning חולין.
                val saved = prefs.lastPlaylistId.takeIf { id -> list.any { it.id == id } }
                val pick = saved ?: list.firstOrNull { it.title.contains("חולין") }?.id.orEmpty()
                _state.update { it.copy(playlists = list, playlistId = pick) }
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update { it.copy(message = "Couldn't load playlists: ${e.message}") }
            }
        }
    }

    fun previewThumbnail() {
        val text = _state.value.thumbText.ifEmpty { return }
        _state.update { it.copy(previewLoading = true) }
        viewModelScope.launch {
            try {
                val bytes = api.thumbnailPreview(text)
                _state.update { it.copy(previewLoading = false, thumbnailPreview = bytes) }
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update { it.copy(previewLoading = false, message = "Preview failed: ${e.message}") }
            }
        }
    }

    /** Download the selected recording from Zoom and upload it to YouTube, in one server-side job. */
    fun publish() {
        val s = _state.value
        val rec = s.selected ?: return
        if (s.publishing || s.title.isEmpty()) return
        _state.update { it.copy(publishing = true, publishStatus = STATUS_TEXT.getValue("queued")) }
        viewModelScope.launch {
            try {
                val result = api.publish(
                    masechet = s.masechet,
                    daf = s.daf.trim(),
                    playlistId = s.playlistId,
                    recordingId = rec.id,
                    description = s.description,
                    privacy = s.privacy,
                    onStatus = { status ->
                        _state.update { it.copy(publishStatus = STATUS_TEXT[status] ?: "Working...") }
                    },
                )
                _state.update { it.copy(publishing = false, publishResult = result) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update {
                    it.copy(
                        publishing = false,
                        message = if (e.retryable) {
                            "Lost contact with the server. The upload may still have succeeded - check YouTube Studio before retrying."
                        } else {
                            "Publishing failed: ${e.message}"
                        },
                    )
                }
            }
        }
    }

    /** After a successful publish: a fresh form and a fresh view of what's left. */
    fun finishPublish() {
        _state.update { it.copy(selected = null, publishResult = null, thumbnailPreview = null, description = "") }
        loadRecordings()
    }

    fun messageShown() = _state.update { it.copy(message = null) }

    /** A 401 that survived the automatic re-login means the stored credentials no longer work. */
    private fun handleAuthFailure(e: ApiException): Boolean {
        if (e.status != 401) return false
        _state.update {
            it.copy(
                screen = Screen.Login, loginError = e.message,
                recordingsLoading = false, publishing = false,
            )
        }
        return true
    }
}
