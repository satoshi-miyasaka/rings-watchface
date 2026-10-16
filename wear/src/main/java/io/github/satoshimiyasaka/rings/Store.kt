package io.github.satoshimiyasaka.rings

import android.content.ComponentName
import android.content.Context
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester

/** The latest events from the phone and the timer, kept on the watch. */
object Store {
    private fun prefs(context: Context) =
        context.getSharedPreferences("rings", Context.MODE_PRIVATE)

    fun events(context: Context): LongArray =
        prefs(context).getString("events", "")!!
            .split(',').filter { it.isNotEmpty() }.map { it.toLong() }.toLongArray()

    fun saveEvents(context: Context, events: LongArray) {
        prefs(context).edit().putString("events", events.joinToString(",")).apply()
        refreshWatchFace(context)
    }

    fun timerEnd(context: Context): Long = prefs(context).getLong("timer_end", 0)

    fun saveTimerEnd(context: Context, end: Long) {
        prefs(context).edit().putLong("timer_end", end).apply()
        refreshWatchFace(context)
    }

    fun refreshWatchFace(context: Context) {
        for (source in listOf(
            HourRingDataSource::class.java,
            WeekADataSource::class.java,
            WeekBDataSource::class.java,
        )) {
            ComplicationDataSourceUpdateRequester
                .create(context, ComponentName(context, source))
                .requestUpdateAll()
        }
    }
}
