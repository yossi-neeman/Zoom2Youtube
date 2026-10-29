package com.neeman.zoom2youtube.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Palette taken from the web app's CSS (templates/index.html, templates/login.html).
val Purple1 = Color(0xFF667EEA)
val Purple2 = Color(0xFF764BA2)
val InkDark = Color(0xFF333333)
val InkMid = Color(0xFF555555)
val InkLight = Color(0xFF666666)
val Hairline = Color(0xFFE0E0E0)
val SelectedBg = Color(0xFFF8F9FF)
val GreenBtn = Color(0xFF28A745)
val SuccessBg = Color(0xFFD4EDDA)
val SuccessFg = Color(0xFF155724)
val SuccessBorder = Color(0xFFC3E6CB)
val ErrorBg = Color(0xFFF8D7DA)
val ErrorFg = Color(0xFF721C24)
val ErrorBorder = Color(0xFFF5C6CB)

val BrandGradient = Brush.linearGradient(listOf(Purple1, Purple2))

private val Light = lightColorScheme(
    primary = Purple1,
    onPrimary = Color.White,
    primaryContainer = SelectedBg,
    onPrimaryContainer = InkDark,
    secondary = Purple2,
    background = Color.White,
    onBackground = InkDark,
    surface = Color.White,
    onSurface = InkDark,
    onSurfaceVariant = InkLight,
    outline = Hairline,
    outlineVariant = Hairline,
    error = Color(0xFFC33333),
)

/** Always light, like the web app - the gradient + white cards look is the brand. */
@Composable
fun Z2YTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Light, content = content)
}

val CardShape = RoundedCornerShape(12.dp)
val FieldShape = RoundedCornerShape(8.dp)

@Composable
fun GradientBackground(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize().background(BrandGradient)) { content() }
}

@Composable
fun WhiteCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = CardShape,
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
    ) {
        Column(Modifier.padding(20.dp), content = content)
    }
}

@Composable
fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Purple1,
    unfocusedBorderColor = Hairline,
    disabledBorderColor = Hairline,
    focusedLabelColor = Purple1,
    unfocusedLabelColor = InkMid,
    disabledLabelColor = InkMid,
    disabledTextColor = InkDark,
    cursorColor = Purple1,
)

/** The web `.btn`: diagonal purple gradient, 8dp corners, bold white label. */
@Composable
fun GradientButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
    brush: Brush = BrandGradient,
) {
    Box(
        modifier
            .fillMaxWidth()
            .alpha(if (enabled) 1f else 0.6f)
            .clip(FieldShape)
            .background(brush)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 24.dp, vertical = 14.dp),
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (loading) CircularProgressIndicator(Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp)
            Text(text, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        }
    }
}

/** Outlined secondary action (Share / Copy etc). */
@Composable
fun OutlineButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    Box(
        modifier
            .alpha(if (enabled) 1f else 0.6f)
            .clip(FieldShape)
            .border(2.dp, Purple1, FieldShape)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = Purple1, fontWeight = FontWeight.SemiBold)
    }
}

/** Web `.alert-success` / `.alert-error`. */
@Composable
fun Alert(text: String, isError: Boolean, modifier: Modifier = Modifier) {
    val (bg, fg, border) = if (isError) Triple(ErrorBg, ErrorFg, ErrorBorder) else Triple(SuccessBg, SuccessFg, SuccessBorder)
    Box(
        modifier
            .fillMaxWidth()
            .clip(FieldShape)
            .background(bg)
            .border(1.dp, border, FieldShape)
            .padding(14.dp),
    ) {
        Text(text, color = fg)
    }
}

/** "📹 Zoom to YouTube" title block on the gradient, same as the web header. */
@Composable
fun BrandHeader(modifier: Modifier = Modifier, trailing: @Composable (() -> Unit)? = null) {
    Column(modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
        if (trailing != null) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) { trailing() }
        }
        Text("📹 Zoom to YouTube", color = Color.White, fontSize = 28.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        Text(
            "Upload Zoom recordings to YouTube",
            color = Color.White.copy(alpha = 0.9f), fontSize = 15.sp, textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 4.dp),
        )
    }
}

/** Translucent pill used for the user name / sign-out in the header (web `.user-info`, `.btn-logout`). */
@Composable
fun GlassPill(text: String, modifier: Modifier = Modifier, onClick: (() -> Unit)? = null) {
    val base = modifier
        .clip(RoundedCornerShape(20.dp))
        .background(Color.White.copy(alpha = 0.2f))
    Box(
        (if (onClick != null) base.clickable(onClick = onClick) else base).padding(horizontal = 14.dp, vertical = 7.dp),
    ) {
        Text(text, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

@Composable
fun FullScreenSpinner() {
    GradientBackground {
        Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator(color = Color.White) }
    }
}
