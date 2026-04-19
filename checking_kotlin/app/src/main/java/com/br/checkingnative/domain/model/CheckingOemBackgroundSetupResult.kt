package com.br.checkingnative.domain.model

data class CheckingOemBackgroundSetupResult(
    val openedSettings: Boolean,
    val message: String,
) {
    companion object {
        val empty: CheckingOemBackgroundSetupResult = CheckingOemBackgroundSetupResult(
            openedSettings = false,
            message = "",
        )
    }
}
