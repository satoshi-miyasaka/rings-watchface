package io.github.satoshimiyasaka.rings

import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.GoalProgressComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import java.time.ZoneId

/** Base for the four sources; each returns a (value, target) pair of packed bits. */
abstract class RingDataSource : SuspendingComplicationDataSourceService() {

    abstract fun values(events: LongArray, now: Long, zone: ZoneId): Pair<Float, Float>

    abstract val label: String

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? {
        if (request.complicationType != ComplicationType.GOAL_PROGRESS) return null
        val (value, target) = values(Store.events(this), System.currentTimeMillis(), ZoneId.systemDefault())
        return data(value, target)
    }

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        if (type == ComplicationType.GOAL_PROGRESS) data(0f, 1f) else null

    // GOAL_PROGRESS data must carry a text, title or image; the watch face
    // ignores it and only reads the two numbers.
    private fun data(value: Float, target: Float): ComplicationData {
        val text = PlainComplicationText.Builder(label).build()
        return GoalProgressComplicationData.Builder(value, target, text)
            .setText(text)
            .build()
    }
}

class HourRingDataSource : RingDataSource() {
    override val label = "Rings hour"
    override fun values(events: LongArray, now: Long, zone: ZoneId) =
        Rings.hourRing(events, now, zone)
}

class WeekADataSource : RingDataSource() {
    override val label = "Rings week A"
    override fun values(events: LongArray, now: Long, zone: ZoneId) =
        Rings.weekA(Rings.weekMasks(events, now, zone))
}

class WeekBDataSource : RingDataSource() {
    override val label = "Rings week B"
    override fun values(events: LongArray, now: Long, zone: ZoneId) =
        Rings.weekB(Rings.weekMasks(events, now, zone))
}

class MinuteRingDataSource : RingDataSource() {
    override val label = "Rings minute"
    override fun values(events: LongArray, now: Long, zone: ZoneId) =
        Rings.minuteRing(events, now, zone)
}
