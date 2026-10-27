package com.neeman.zoom2youtube

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.neeman.zoom2youtube.ui.AppViewModel
import com.neeman.zoom2youtube.ui.FullScreenSpinner
import com.neeman.zoom2youtube.ui.LoginScreen
import com.neeman.zoom2youtube.ui.RecordingsScreen
import com.neeman.zoom2youtube.ui.Screen
import com.neeman.zoom2youtube.ui.UploadScreen
import com.neeman.zoom2youtube.ui.Z2YTheme

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Light status/nav bar icons over the purple gradient.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        // A cold start from the Google sign-in redirect; a recreated activity must not replay it.
        if (savedInstanceState == null) handleSignInRedirect(intent)
        setContent {
            Z2YTheme {
                val state by vm.state.collectAsStateWithLifecycle()
                BackHandler(enabled = state.screen == Screen.Upload) { vm.backToRecordings() }
                when (state.screen) {
                    Screen.Booting -> FullScreenSpinner()
                    Screen.Login -> LoginScreen(state, vm)
                    Screen.Recordings -> RecordingsScreen(state, vm)
                    Screen.Upload -> UploadScreen(state, vm)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleSignInRedirect(intent)
    }

    /** `z2y://login?code=...` is what the server redirects to after Google sign-in. */
    private fun handleSignInRedirect(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme != "z2y" || uri.host != "login") return
        intent.data = null
        uri.getQueryParameter("code")?.takeIf { it.isNotEmpty() }?.let(vm::completeGoogleSignIn)
    }
}
