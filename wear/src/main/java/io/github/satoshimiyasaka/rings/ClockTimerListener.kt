package io.github.satoshimiyasaka.rings

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

/**
 * Watches the Clock app's timer notification and passes its end time to the
 * minute ring. Needs notification access, granted in the watch settings or with
 * `adb shell cmd notification allow_listener`.
 */
class ClockTimerListener : NotificationListenerService() {

    override fun onListenerConnected() = update()

    override fun onListenerDisconnected() = Store.saveTimerEnd(this, 0)

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == ClockTimer.CLOCK_PACKAGE) update()
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        if (sbn.packageName == ClockTimer.CLOCK_PACKAGE) update()
    }

    private fun update() {
        val shown = (activeNotifications ?: emptyArray()).map {
            val extras = it.notification.extras
            ClockTimer.Shown(
                it.packageName,
                extras.getBoolean(Notification.EXTRA_CHRONOMETER_COUNT_DOWN),
                extras.getBoolean(Notification.EXTRA_SHOW_CHRONOMETER),
                it.notification.`when`,
            )
        }
        val end = ClockTimer.end(shown, System.currentTimeMillis())
        if (end != Store.timerEnd(this)) Store.saveTimerEnd(this, end)
    }
}
