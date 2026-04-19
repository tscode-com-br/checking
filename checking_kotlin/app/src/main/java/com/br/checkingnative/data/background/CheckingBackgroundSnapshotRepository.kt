package com.br.checkingnative.data.background

import com.br.checkingnative.domain.model.CheckingState
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

@Singleton
class CheckingBackgroundSnapshotRepository @Inject constructor() {
    private val _snapshots = MutableSharedFlow<CheckingState>(
        replay = 1,
        extraBufferCapacity = 16,
    )

    val snapshots: SharedFlow<CheckingState> = _snapshots.asSharedFlow()

    suspend fun publish(state: CheckingState) {
        _snapshots.emit(state)
    }

    fun tryPublish(state: CheckingState) {
        _snapshots.tryEmit(state)
    }
}
