package com.br.checkingnative.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Typography = Typography(
    headlineMedium = TextStyle(
        fontSize = 32.sp,
        fontWeight = FontWeight.W700,
        color = CheckingText,
        lineHeight = 34.sp,
    ),
    bodyMedium = TextStyle(
        fontSize = 15.sp,
        color = CheckingMuted,
    ),
    titleSmall = TextStyle(
        fontSize = 13.sp,
        fontWeight = FontWeight.W600,
        color = CheckingMuted,
    ),
)
