package io.github.satoshimiyasaka.rings

import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.GoalProgressComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService.ComplicationRequestListener
import androidx.wear.watchface.complications.datasource.ComplicationDataTimeline
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.TimeInterval
import androidx.wear.watchface.complications.datasource.TimelineEntry
import java.time.Instant
import java.time.ZoneId

/**
 * Base for the four sources; each returns a (value, target) pair of packed bits.
 *
 * The watch does not keep to UPDATE_PERIOD_SECONDS, so the rings would stay
 * on an old lap until the next update happened to come. Each answer is
 * therefore a timeline of the coming day, one entry per stretch with the same
 * values, and the watch picks the entry for the current time when it draws.
 * In the five-minute mode the timeline has a step every five minutes.
 */
abstract class RingDataSource : ComplicationDataSourceService() {

    abstract fun values(inputs: Inputs, now: Long, zone: ZoneId): Pair<Float, Float>

    abstract val label: String

    override fun onComplicationRequest(request: ComplicationRequest, listener: ComplicationRequestListener) {
        if (request.complicationType != ComplicationType.GOAL_PROGRESS) {
            listener.onComplicationData(null)
            return
        }
        val inputs = Store.inputs(this)
        val zone = ZoneId.systemDefault()
        val step = if (inputs.mode == MODE_EVERY_FIVE_MINUTES) 5L else 60L
        val times = Rings.switchTimes(System.currentTimeMillis(), zone, stepMinutes = step)
        val values = times.dropLast(1).map { values(inputs, it, zone) }
        val entries = ArrayList<TimelineEntry>()
        var from = 0
        for (i in 1..values.size) {
            if (i < values.size && values[i] == values[from]) continue
            val validity = TimeInterval(Instant.ofEpochMilli(times[from]), Instant.ofEpochMilli(times[i]))
            entries += TimelineEntry(validity, data(values[from]))
            from = i
        }
        listener.onComplicationDataTimeline(ComplicationDataTimeline(data(values[0]), entries))
    }

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        if (type == ComplicationType.GOAL_PROGRESS) data(0f to 1f) else null

    // GOAL_PROGRESS data must carry a text, title or image; the watch face
    // ignores it and only reads the two numbers.
    private fun data(values: Pair<Float, Float>): ComplicationData {
        val text = PlainComplicationText.Builder(label).build()
        return GoalProgressComplicationData.Builder(values.first, values.second, text)
            .setText(text)
            .build()
    }
}

private val Inputs.rolling get() = mode == MODE_EVERY_FIVE_MINUTES

class HourRingDataSource : RingDataSource() {
    override val label = "Rings hour"
    override fun values(inputs: Inputs, now: Long, zone: ZoneId) =
        Rings.hourRing(inputs.events, now, zone, inputs.rolling)
}

class WeekADataSource : RingDataSource() {
    override val label = "Rings week A"
    override fun values(inputs: Inputs, now: Long, zone: ZoneId) =
        Rings.weekA(Rings.weekMasks(inputs.events, now, zone))
}

class WeekBDataSource : RingDataSource() {
    override val label = "Rings week B"
    override fun values(inputs: Inputs, now: Long, zone: ZoneId) =
        Rings.weekB(Rings.weekMasks(inputs.events, now, zone), Rings.daysOffFlags(inputs.daysOff, now, zone))
}

class MinuteRingDataSource : RingDataSource() {
    override val label = "Rings minute"
    override fun values(inputs: Inputs, now: Long, zone: ZoneId) =
        Rings.minuteRing(
            inputs.events, now, zone, inputs.rolling,
            Rings.phoneBatteryBits(inputs.phoneBattery, inputs.syncedAt, now),
        )
}
