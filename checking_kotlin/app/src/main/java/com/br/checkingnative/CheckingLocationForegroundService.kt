package com.br.checkingnative

import android.app.Service
import android.content.Intent
import android.os.IBinder

class CheckingLocationForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf(startId)
            return START_NOT_STICKY
        }

        stopSelf(startId)
        return START_NOT_STICKY
    }

    companion object {
        const val ACTION_START: String = "com.br.checkingnative.location.START"
        const val ACTION_STOP: String = "com.br.checkingnative.location.STOP"
        const val CHANNEL_ID: String = "checking_location_tracking"
        const val NOTIFICATION_ID: Int = 4012
    }
}
