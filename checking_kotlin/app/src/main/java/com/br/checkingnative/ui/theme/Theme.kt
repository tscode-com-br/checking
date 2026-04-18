package com.br.checkingnative.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = CheckingBlue,
    onPrimary = CheckingCard,
    primaryContainer = CheckingBlueLight,
    onPrimaryContainer = CheckingText,
    background = CheckingSurface,
    onBackground = CheckingText,
    surface = CheckingCard,
    onSurface = CheckingText,
    onSurfaceVariant = CheckingMuted,
)

private val DarkColorScheme = darkColorScheme(
    primary = CheckingBlueLight,
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

