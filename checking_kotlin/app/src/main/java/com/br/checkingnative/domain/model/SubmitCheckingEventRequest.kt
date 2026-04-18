package com.br.checkingnative.domain.model

import java.time.Instant

data class SubmitCheckingEventRequest(
    val chave: String,
    val projeto: ProjetoType,
    val action: RegistroType,
    val informe: InformeType,
    val clientEventId: String,
    val eventTime: Instant,
    val local: String? = null,
)
