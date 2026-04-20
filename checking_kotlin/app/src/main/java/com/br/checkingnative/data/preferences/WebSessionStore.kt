package com.br.checkingnative.data.preferences

import kotlinx.coroutines.flow.Flow

data class WebSessionSnapshot(
    val cookieHeader: String = "",
)

interface WebSessionStore {
    val webSessionSnapshot: Flow<WebSessionSnapshot>

    suspend fun saveWebSessionCookieHeader(cookieHeader: String)

    suspend fun clearWebSessionCookie()
}
