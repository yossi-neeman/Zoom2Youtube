package com.neeman.zoom2youtube.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neeman.zoom2youtube.data.Recording
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@Composable
fun RecordingsScreen(state: UiState, vm: AppViewModel) {
    val snackbar = remember { SnackbarHostState() }
    SnackbarEffect(state.message, snackbar, vm)

    GradientBackground {
        Scaffold(
            containerColor = Color.Transparent,
            snackbarHost = { SnackbarHost(snackbar) },
        ) { padding ->
            Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
                BrandHeader(Modifier.padding(top = 8.dp, bottom = 16.dp)) {
                    if (state.username.isNotEmpty()) GlassPill("👤 ${state.username}", Modifier.weight(1f, fill = false))
                    Spacer(Modifier.size(8.dp))
                    GlassPill("Logout", onClick = vm::signOut)
                }

                WhiteCard(Modifier.weight(1f, fill = false)) {
                    TabsRow(
                        activeUpload = false, uploadEnabled = state.downloaded != null,
                        onRecordings = {}, onUpload = vm::openUpload,
                    )
                    Spacer(Modifier.height(16.dp))
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text("Available Zoom Recordings", color = InkDark, fontSize = 20.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        Text(
                            "↻", color = Purple1, fontSize = 26.sp,
                            modifier = Modifier.clickable(enabled = !state.recordingsLoading, onClick = vm::loadRecordings).padding(6.dp),
                        )
                    }
                    Spacer(Modifier.height(10.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        listOf(1, 5, 7, 30).forEach { d ->
                            FilterChip(
                                selected = state.days == d,
                                onClick = { vm.setDays(d) },
                                label = { Text(if (d == 1) "1 day" else "$d days") },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = SelectedBg, selectedLabelColor = Purple1,
                                ),
                                border = FilterChipDefaults.filterChipBorder(
                                    enabled = true, selected = state.days == d,
                                    borderColor = Hairline, selectedBorderColor = Purple1,
                                    borderWidth = 2.dp, selectedBorderWidth = 2.dp,
                                ),
                            )
                        }
                    }
                    Spacer(Modifier.height(14.dp))

                    when {
                        state.recordingsLoading -> Box(Modifier.fillMaxWidth().padding(40.dp), Alignment.Center) {
                            CircularProgressIndicator(color = Purple1)
                        }
                        state.recordingsError != null -> Alert(state.recordingsError, isError = true)
                        state.recordings.isEmpty() -> Text("No recordings found in the selected time range.", color = InkLight)
                        else -> LazyColumn(
                            Modifier.weight(1f, fill = false),
                            verticalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            items(state.recordings, key = { it.id }) { rec ->
                                RecordingItem(rec, selected = rec.id == state.selected?.id, onClick = { vm.select(rec) })
                            }
                        }
                    }

                    if (state.selected != null) {
                        Spacer(Modifier.height(16.dp))
                        GradientButton(
                            if (state.downloading) "Downloading on the server..." else "Download Selected Recording",
                            onClick = vm::downloadSelected,
                            enabled = !state.downloading,
                            loading = state.downloading,
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

/** Web `.recording-item`. */
@Composable
private fun RecordingItem(rec: Recording, selected: Boolean, onClick: () -> Unit) {
    val shape = RoundedCornerShape(8.dp)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(if (selected) SelectedBg else Color.White)
            .border(2.dp, if (selected) Purple1 else Hairline, shape)
            .clickable(onClick = onClick)
            .padding(15.dp),
    ) {
        Text(rec.topic, color = InkDark, fontSize = 17.sp, fontWeight = FontWeight.SemiBold)
        Text("📅 ${formatTime(rec.startTime)}  ⏱ ${rec.durationMin} min", color = InkLight, fontSize = 14.sp, modifier = Modifier.padding(top = 4.dp))
    }
}

private fun formatTime(iso: String): String = try {
    DateTimeFormatter.ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
        .withZone(ZoneId.systemDefault())
        .format(Instant.parse(iso))
} catch (e: Exception) {
    iso
}

@Composable
internal fun SnackbarEffect(message: String?, host: SnackbarHostState, vm: AppViewModel) {
    LaunchedEffect(message) {
        if (message != null) {
            host.showSnackbar(message)
            vm.messageShown()
        }
    }
}
