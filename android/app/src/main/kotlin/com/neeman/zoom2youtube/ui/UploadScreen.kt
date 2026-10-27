package com.neeman.zoom2youtube.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neeman.zoom2youtube.data.SEDARIM
import com.neeman.zoom2youtube.data.UploadResult

private val PRIVACY = listOf("public" to "Public", "unlisted" to "Unlisted", "private" to "Private")

@Composable
fun UploadScreen(state: UiState, vm: AppViewModel) {
    val snackbar = remember { SnackbarHostState() }
    SnackbarEffect(state.message, snackbar, vm)
    KeepScreenOn(state.uploading)

    GradientBackground {
        Scaffold(
            containerColor = Color.Transparent,
            snackbarHost = { SnackbarHost(snackbar) },
        ) { padding ->
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .imePadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
            ) {
                BrandHeader(Modifier.padding(top = 8.dp, bottom = 16.dp)) {
                    if (state.username.isNotEmpty()) GlassPill("👤 ${state.username}", Modifier.weight(1f, fill = false))
                    Spacer(Modifier.size(8.dp))
                    GlassPill("Logout", onClick = { if (!state.uploading) vm.signOut() })
                }
                WhiteCard {
                    TabsRow(
                        activeUpload = true, uploadEnabled = true,
                        onRecordings = { if (!state.uploading) vm.backToRecordings() }, onUpload = {},
                    )
                    Spacer(Modifier.height(16.dp))
                    Text("Upload to YouTube", color = InkDark, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(14.dp))

                    state.downloaded?.let {
                        // Web "📹 Downloaded Recording" box.
                        Column(
                            Modifier
                                .fillMaxWidth()
                                .clip(FieldShape)
                                .background(SelectedBg)
                                .border(2.dp, Purple1, FieldShape)
                                .padding(14.dp),
                        ) {
                            Text("📹 Downloaded Recording", color = InkDark, fontWeight = FontWeight.SemiBold)
                            Text(it.recording.topic, color = InkLight, fontSize = 14.sp, modifier = Modifier.padding(top = 2.dp))
                        }
                        Spacer(Modifier.height(16.dp))
                    }

                    val result = state.uploadResult
                    if (result != null) {
                        SuccessCard(result, onDone = vm::finishUpload)
                    } else {
                        UploadForm(state, vm)
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
        }
    }
}

@Composable
private fun UploadForm(state: UiState, vm: AppViewModel) {
    val enabled = !state.uploading
    val hebrew = TextStyle(textDirection = TextDirection.Content)

    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        DropdownField(label = "מסכת *", value = state.masechet, enabled = enabled, textStyle = hebrew) { close ->
            SEDARIM.forEach { seder ->
                Text(
                    seder.name,
                    style = MaterialTheme.typography.labelLarge,
                    color = Purple1,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                )
                seder.masechtot.forEach { m ->
                    DropdownMenuItem(text = { Text(m, style = hebrew) }, onClick = { vm.setMasechet(m); close() })
                }
                HorizontalDivider(color = Hairline)
            }
        }

        OutlinedTextField(
            value = state.daf, onValueChange = vm::setDaf,
            label = { Text("דף *") }, placeholder = { Text("קיט") },
            singleLine = true, enabled = enabled, textStyle = hebrew,
            shape = FieldShape, colors = fieldColors(),
            modifier = Modifier.fillMaxWidth(),
        )

        OutlinedTextField(
            value = state.title, onValueChange = {}, readOnly = true,
            label = { Text("Video title") }, placeholder = { Text("Choose מסכת and דף") },
            textStyle = hebrew, shape = FieldShape, colors = fieldColors(),
            modifier = Modifier.fillMaxWidth(),
        )

        OutlinedTextField(
            value = state.description, onValueChange = vm::setDescription,
            label = { Text("Description (optional)") }, minLines = 3,
            enabled = enabled, shape = FieldShape, colors = fieldColors(),
            modifier = Modifier.fillMaxWidth(),
        )

        DropdownField(label = "Privacy", value = PRIVACY.first { it.first == state.privacy }.second, enabled = enabled) { close ->
            PRIVACY.forEach { (key, name) ->
                DropdownMenuItem(text = { Text(name) }, onClick = { vm.setPrivacy(key); close() })
            }
        }

        DropdownField(
            label = "Playlist (optional)",
            value = state.playlists.firstOrNull { it.id == state.playlistId }?.let { "${it.title} (${it.itemCount} videos)" }
                ?: "No playlist",
            enabled = enabled, textStyle = hebrew,
        ) { close ->
            DropdownMenuItem(text = { Text("No playlist") }, onClick = { vm.setPlaylist(""); close() })
            state.playlists.forEach { p ->
                DropdownMenuItem(
                    text = { Text("${p.title} (${p.itemCount} videos)", style = hebrew) },
                    onClick = { vm.setPlaylist(p.id); close() },
                )
            }
        }

        // Thumbnail: text is derived from מסכת/דף; the server renders it so what you see is what uploads.
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlineButton(
                "🖼 Preview thumbnail",
                onClick = vm::previewThumbnail,
                enabled = enabled && state.thumbText.isNotEmpty() && !state.previewLoading,
            )
            if (state.previewLoading) CircularProgressIndicator(Modifier.size(24.dp), color = Purple1, strokeWidth = 3.dp)
        }
        state.thumbnailPreview?.let { bytes ->
            val bitmap = remember(bytes) { BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap() }
            if (bitmap != null) {
                Image(
                    bitmap, contentDescription = "Thumbnail preview",
                    modifier = Modifier.fillMaxWidth().clip(FieldShape),
                )
            }
        }

        if (state.uploading) {
            LinearProgressIndicator(
                Modifier.fillMaxWidth().height(10.dp).clip(RoundedCornerShape(5.dp)),
                color = Purple1, trackColor = Hairline,
            )
            Text(state.uploadStatus, color = InkDark)
            Text(
                "You can keep this screen open; the server continues even if the connection drops.",
                fontSize = 13.sp, color = InkLight,
            )
        }

        GradientButton(
            if (state.uploading) "Uploading..." else "Upload to YouTube",
            onClick = vm::upload,
            enabled = enabled && state.title.isNotEmpty(),
            loading = state.uploading,
        )
    }
}

@Composable
private fun SuccessCard(result: UploadResult, onDone: () -> Unit) {
    val context = LocalContext.current
    Column(
        Modifier
            .fillMaxWidth()
            .clip(FieldShape)
            .background(SuccessBg)
            .border(1.dp, SuccessBorder, FieldShape)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("✓ Upload Complete!", color = SuccessFg, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
        Text("The video is on YouTube and has been deleted from the server.", color = SuccessFg)
        Text(result.videoUrl, color = SuccessFg, fontSize = 14.sp)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlineButton("Open", onClick = {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.videoUrl)))
            })
            OutlineButton("Share", onClick = {
                val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, result.videoUrl)
                context.startActivity(Intent.createChooser(send, null))
            })
            OutlineButton("Copy", onClick = {
                val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("YouTube URL", result.videoUrl))
            })
        }
        GradientButton("OK", onClick = onDone, brush = Brush.linearGradient(listOf(GreenBtn, GreenBtn)))
    }
}

/** Read-only text field that opens a dropdown menu; [content] receives a `close` callback. */
@Composable
private fun DropdownField(
    label: String,
    value: String,
    enabled: Boolean,
    textStyle: TextStyle = TextStyle.Default,
    content: @Composable ColumnScope.(close: () -> Unit) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedTextField(
            value = value, onValueChange = {}, readOnly = true, enabled = enabled,
            label = { Text(label) }, textStyle = textStyle,
            shape = FieldShape, colors = fieldColors(),
            trailingIcon = { Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = InkLight) },
            modifier = Modifier.fillMaxWidth(),
        )
        // A transparent layer on top catches the tap (a disabled-looking field can't).
        Box(Modifier.matchParentSize().clickable(enabled = enabled) { expanded = true })
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }, containerColor = Color.White) {
            content { expanded = false }
        }
    }
}

@Composable
private fun KeepScreenOn(on: Boolean) {
    val view = LocalView.current
    DisposableEffect(on) {
        view.keepScreenOn = on
        onDispose { view.keepScreenOn = false }
    }
}
