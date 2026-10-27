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

enum class Screen { Booting, Login, Recordings, Upload }

data class Downloaded(val recording: Recording, val filepath: String)

data class UiState(
    val screen: Screen = Screen.Booting,

    // login
    val serverUrl: String = "",
    val username: String = "",
    val loginBusy: Boolean = false,
    val loginError: String? = null,

    // recordings
    val days: Int = 5,
    val recordings: List<Recording> = emptyList(),
    val recordingsLoading: Boolean = false,
    val recordingsError: String? = null,
    val selected: Recording? = null,
    val downloading: Boolean = false,

    // upload form
    val downloaded: Downloaded? = null,
    val masechet: String = "",
    val daf: String = "",
    val description: String = "",
    val privacy: String = "public",
    val playlists: List<Playlist> = emptyList(),
    val playlistId: String = "",
    val thumbnailPreview: ByteArray? = null,
    val previewLoading: Boolean = false,
    val uploading: Boolean = false,
    val uploadStatus: String = "",
    val uploadResult: UploadResult? = null,

    /** One-shot message for a snackbar; cleared by [AppViewModel.messageShown]. */
    val message: String? = null,
) {
    val title get() = if (masechet.isNotBlank() && daf.isNotBlank()) videoTitle(masechet, daf.trim()) else ""
    val thumbText get() = if (masechet.isNotBlank() && daf.isNotBlank()) thumbnailText(masechet, daf.trim()) else ""
}

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
                    _state.update { it.copy(screen = Screen.Recordings) }
                    loadRecordings()
                } catch (e: ApiException) {
                    _state.update { it.copy(screen = Screen.Login, loginError = e.message) }
                }
            }
            prefs.authMode == Prefs.MODE_GOOGLE && prefs.cookies != null -> {
                // No password to fall back on: the saved session cookie either still works or we ask again.
                api.resumeSession(prefs.serverUrl)
                _state.update { it.copy(screen = Screen.Recordings) }
                loadRecordings()
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
                _state.update {
                    it.copy(
                        screen = Screen.Recordings, loginBusy = false,
                        serverUrl = prefs.serverUrl, username = username,
                    )
                }
                loadRecordings()
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
                _state.update { it.copy(screen = Screen.Recordings, loginBusy = false, username = email) }
                loadRecordings()
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
                val list = api.recordings(days)
                _state.update { s ->
                    s.copy(
                        recordings = list, recordingsLoading = false,
                        selected = s.selected?.takeIf { sel -> list.any { it.id == sel.id } },
                    )
                }
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update { it.copy(recordingsLoading = false, recordingsError = e.message) }
            }
        }
    }

    fun select(recording: Recording) = _state.update { it.copy(selected = recording) }

    fun downloadSelected() {
        val rec = _state.value.selected ?: return
        if (_state.value.downloading) return
        _state.update { it.copy(downloading = true) }
        viewModelScope.launch {
            try {
                val result = api.download(rec.id)
                _state.update {
                    it.copy(
                        downloading = false,
                        downloaded = Downloaded(rec, result.filepath),
                        screen = Screen.Upload,
                        uploadResult = null,
                        thumbnailPreview = null,
                        message = if (result.alreadyExists) "Recording was already downloaded - using the existing file" else null,
                    )
                }
                loadPlaylists()
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                val msg = if (e.retryable) {
                    "The connection dropped during the download. The server may still be fetching it - " +
                        "wait a minute and check it finished before uploading."
                } else {
                    e.message ?: "Download failed"
                }
                _state.update { it.copy(downloading = false, message = msg) }
            }
        }
    }

    // ---- upload form ----

    fun openUpload() {
        if (_state.value.downloaded != null) _state.update { it.copy(screen = Screen.Upload) }
    }

    fun backToRecordings() {
        if (_state.value.uploading) return
        _state.update { it.copy(screen = Screen.Recordings) }
    }

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

    fun upload() {
        val s = _state.value
        val file = s.downloaded?.filepath ?: return
        if (s.uploading || s.title.isEmpty()) return
        _state.update { it.copy(uploading = true, uploadStatus = "Uploading to YouTube - this can take several minutes") }
        viewModelScope.launch {
            try {
                val result = api.upload(
                    videoFile = file,
                    title = s.title,
                    description = s.description,
                    privacy = s.privacy,
                    playlistId = s.playlistId,
                    thumbnailText = s.thumbText,
                    onReconnect = { n ->
                        _state.update { it.copy(uploadStatus = "Still uploading on the server (reconnect #$n)...") }
                    },
                )
                _state.update { it.copy(uploading = false, uploadResult = result) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ApiException) {
                if (handleAuthFailure(e)) return@launch
                _state.update {
                    it.copy(
                        uploading = false,
                        message = if (e.retryable) {
                            "Lost contact with the server. The upload may still have succeeded - check YouTube Studio before retrying."
                        } else {
                            "Upload failed: ${e.message}"
                        },
                    )
                }
            }
        }
    }

    /** After a successful upload: back to the list, with a fresh view of what's left. */
    fun finishUpload() {
        _state.update {
            it.copy(
                screen = Screen.Recordings, downloaded = null, selected = null,
                uploadResult = null, thumbnailPreview = null, description = "",
            )
        }
        loadRecordings()
    }

    fun messageShown() = _state.update { it.copy(message = null) }

    /** A 401 that survived the automatic re-login means the stored credentials no longer work. */
    private fun handleAuthFailure(e: ApiException): Boolean {
        if (e.status != 401) return false
        _state.update {
            it.copy(
                screen = Screen.Login, loginError = e.message,
                recordingsLoading = false, downloading = false, uploading = false,
            )
        }
        return true
    }
}
