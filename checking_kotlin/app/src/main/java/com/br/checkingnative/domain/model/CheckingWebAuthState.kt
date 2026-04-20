package com.br.checkingnative.domain.model

data class CheckingWebAuthState(
    val chave: String = "",
    val found: Boolean = false,
    val hasPassword: Boolean = false,
    val authenticated: Boolean = false,
    val hasStoredSession: Boolean = false,
    val isChecking: Boolean = false,
    val isAuthenticating: Boolean = false,
    val message: String = "",
) {
    val needsLogin: Boolean
        get() = found && hasPassword && !authenticated

    val needsPasswordRegistration: Boolean
        get() = found && !hasPassword && !authenticated

    val needsUserRegistration: Boolean
        get() = chave.length == 4 && !found && !authenticated && !isChecking

    companion object {
        fun initial(): CheckingWebAuthState = CheckingWebAuthState()

        fun awaitingChave(): CheckingWebAuthState {
            return CheckingWebAuthState(
                message = "Informe a chave para verificar o acesso web.",
            )
        }

        fun checking(chave: String, previous: CheckingWebAuthState): CheckingWebAuthState {
            return previous.copy(
                chave = chave,
                isChecking = true,
                isAuthenticating = false,
                message = "Verificando acesso web.",
            )
        }

        fun authenticating(previous: CheckingWebAuthState): CheckingWebAuthState {
            return previous.copy(
                isChecking = false,
                isAuthenticating = true,
            )
        }

        fun fromStatus(
            response: WebPasswordStatusResponse,
            hasStoredSession: Boolean,
        ): CheckingWebAuthState {
            return CheckingWebAuthState(
                chave = response.chave,
                found = response.found,
                hasPassword = response.hasPassword,
                authenticated = response.authenticated,
                hasStoredSession = hasStoredSession && response.authenticated,
                isChecking = false,
                isAuthenticating = false,
                message = response.message,
            )
        }

        fun fromAction(
            chave: String,
            response: WebPasswordActionResponse,
            hasStoredSession: Boolean,
        ): CheckingWebAuthState {
            return CheckingWebAuthState(
                chave = chave,
                found = true,
                hasPassword = response.hasPassword,
                authenticated = response.authenticated,
                hasStoredSession = hasStoredSession && response.authenticated,
                isChecking = false,
                isAuthenticating = false,
                message = response.message,
            )
        }

        fun unauthenticated(
            chave: String,
            message: String,
            found: Boolean = true,
            hasPassword: Boolean = true,
        ): CheckingWebAuthState {
            return CheckingWebAuthState(
                chave = chave,
                found = found,
                hasPassword = hasPassword,
                authenticated = false,
                hasStoredSession = false,
                isChecking = false,
                isAuthenticating = false,
                message = message,
            )
        }
    }
}

data class CheckingWebRegistrationInput(
    val nome: String,
    val projeto: ProjetoType,
    val endRua: String,
    val zip: String,
    val email: String,
    val senha: String,
    val confirmarSenha: String,
)
