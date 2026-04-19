package com.br.checkingnative

import android.content.Context
import android.content.Intent

object GeoActionContract {
    const val ACTION_GEO: String = "com.br.checkingnative.GEO_ACTION"
    const val EXTRA_GEO_ACTION: String = "geo_action"
    const val EXTRA_NOTIFICATION_ID: String = "notification_id"

    private const val BRING_TO_FRONT_FLAGS: Int =
        Intent.FLAG_ACTIVITY_NEW_TASK or
            Intent.FLAG_ACTIVITY_CLEAR_TOP or
            Intent.FLAG_ACTIVITY_SINGLE_TOP

    fun newIntent(
        context: Context,
        actionType: String,
        notificationId: Int? = null,
    ): Intent {
        return Intent(context, MainActivity::class.java).apply {
            action = ACTION_GEO
            putExtra(EXTRA_GEO_ACTION, actionType)
            if (notificationId != null) {
                putExtra(EXTRA_NOTIFICATION_ID, notificationId)
            }
            flags = BRING_TO_FRONT_FLAGS
        }
    }

    fun readAction(intent: Intent?): String? {
        if (intent?.action != ACTION_GEO) {
            return null
        }
        return intent.getStringExtra(EXTRA_GEO_ACTION)
            ?.trim()
            ?.takeIf { value -> value.isNotEmpty() }
    }

    fun readNotificationId(intent: Intent?): Int {
        if (intent?.action != ACTION_GEO) {
            return 0
        }
        return intent.getIntExtra(EXTRA_NOTIFICATION_ID, 0)
    }
}
