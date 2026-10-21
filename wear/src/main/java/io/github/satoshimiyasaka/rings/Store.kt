package io.github.satoshimiyasaka.rings

import android.content.ComponentName
import android.content.Context
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester

/** The latest sync from the phone, kept on the watch. */
object Store {
    private fun prefs(context: Context) =
        context.getSharedPreferences("rings", Context.MODE_PRIVATE)

    private fun longs(text: String?): LongArray =
        text.orEmpty().split(',').filter { it.isNotEmpty() }.map { it.toLong() }.toLongArray()

    fun inputs(context: Context): Inputs {
        val prefs = prefs(context)
        return Inputs(
            events = longs(prefs.getString("events", "")),
            daysOff = longs(prefs.getString("days_off", "")),
            phoneBattery = prefs.getInt("phone_battery", -1),
            syncedAt = prefs.getLong("synced_at", 0),
            mode = prefs.getInt("mode", MODE_PER_LAP),
        )
    }

    fun save(context: Context, inputs: Inputs) {
        prefs(context).edit()
            .putString("events", inputs.events.joinToString(","))
            .putString("days_off", inputs.daysOff.joinToString(","))
            .putInt("phone_battery", inputs.phoneBattery)
            .putLong("synced_at", inputs.syncedAt)
            .putInt("mode", inputs.mode)
            .apply()
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
