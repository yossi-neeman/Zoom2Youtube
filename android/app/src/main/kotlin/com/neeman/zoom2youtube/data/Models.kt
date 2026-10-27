package com.neeman.zoom2youtube.data

data class Recording(
    val id: String,
    val topic: String,
    val startTime: String,
    val durationMin: Int,
)

data class Playlist(val id: String, val title: String, val itemCount: Int)

data class DownloadResult(val filepath: String, val alreadyExists: Boolean)

data class UploadResult(val videoId: String, val videoUrl: String)

class ApiException(
    message: String,
    val status: Int = 0,
    /** True for transient failures (proxy timeouts, dropped connections) that are safe to ask again. */
    val retryable: Boolean = false,
) : Exception(message)
