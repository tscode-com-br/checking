package com.br.checkingnative.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = CheckingPrimary,
    onPrimary = CheckingCard,
    primaryContainer = CheckingPrimarySoft,
    onPrimaryContainer = CheckingText,
    background = CheckingBackground,
    onBackground = CheckingText,
    surface = CheckingCard,
    onSurface = CheckingText,
    onSurfaceVariant = CheckingMuted,
    outline = CheckingBorder,
    error = CheckingError,
)

private val DarkColorScheme = darkColorScheme(
    primary = CheckingPrimarySoft,
)

@Composable
fun CheckingKotlinTheme(
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        typography = Typography,
        content = content,
    )
}
