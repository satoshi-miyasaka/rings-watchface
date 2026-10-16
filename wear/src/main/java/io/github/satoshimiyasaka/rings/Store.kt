package io.github.satoshimiyasaka.rings

import android.content.ComponentName
import android.content.Context
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester

/** The latest events from the phone, kept on the watch. */
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

    /** Whether the face shows the past instead of the coming hours and days. */
    fun past(context: Context): Boolean = prefs(context).getBoolean("past", false)

    /** When the face was last tapped, to log how long the switch takes. */
    fun tappedAt(context: Context): Long = prefs(context).getLong("tappedAt", 0L)

    fun togglePast(context: Context, now: Long) {
        prefs(context).edit()
            .putBoolean("past", !past(context))
            .putLong("tappedAt", now)
            .commit()
        refreshWatchFace(context)
    }

    fun refreshWatchFace(context: Context) {
        for (source in listOf(
            HourRingDataSource::class.java,
            WeekADataSource::class.java,
            WeekBDataSource::class.java,
            MinuteRingDataSource::class.java,
        )) {
            ComplicationDataSourceUpdateRequester
                .create(context, ComponentName(context, source))
                .requestUpdateAll()
        }
    }
}
