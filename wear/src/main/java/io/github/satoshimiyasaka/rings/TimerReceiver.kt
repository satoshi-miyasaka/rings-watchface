package io.github.satoshimiyasaka.rings

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.VibrationEffect
import android.os.VibratorManager

/** Starts, stops and finishes the timer shown on the minute ring. */
class TimerReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        Store.saveTimerEnd(context, 0)
        context.getSystemService(VibratorManager::class.java)?.defaultVibrator?.vibrate(
            VibrationEffect.createWaveform(longArrayOf(0, 400, 200, 400, 200, 400), -1),
        )
    }

    companion object {
        private fun pending(context: Context) = PendingIntent.getBroadcast(
            context, 0, Intent(context, TimerReceiver::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        /** Adds [minutes] to the running timer, or starts one. */
        fun add(context: Context, minutes: Int) {
            val now = System.currentTimeMillis()
            val end = maxOf(now, Store.timerEnd(context)) + minutes * 60_000L
            Store.saveTimerEnd(context, end)
            context.getSystemService(AlarmManager::class.java)
                .setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, end, pending(context))
        }

        fun cancel(context: Context) {
            context.getSystemService(AlarmManager::class.java).cancel(pending(context))
            Store.saveTimerEnd(context, 0)
        }
    }
}
