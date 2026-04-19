package com.br.checkingnative

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

class BootCompletedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
            -> {
                ScheduledNotificationReceiver.rescheduleStoredAlarms(context)
                startLocationForegroundService(context)
            }
        }
    }

    private fun startLocationForegroundService(context: Context) {
        runCatching {
            ContextCompat.startForegroundService(
                context,
                Intent(context, CheckingLocationForegroundService::class.java).apply {
                    action = CheckingLocationForegroundService.ACTION_START
                },
            )
        }
    }
}
