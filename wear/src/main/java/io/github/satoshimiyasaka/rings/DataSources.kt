package io.github.satoshimiyasaka.rings

import android.app.PendingIntent
import android.content.Intent
import android.util.Log
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.GoalProgressComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService
import java.time.ZoneId

/** Base for the four sources; each returns a (value, target) pair of packed bits. */
abstract class RingDataSource : SuspendingComplicationDataSourceService() {

    abstract fun values(events: LongArray, now: Long, zone: ZoneId, past: Boolean): Pair<Float, Float>

    abstract val label: String

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? {
        if (request.complicationType != ComplicationType.GOAL_PROGRESS) return null
        val now = System.currentTimeMillis()
        val past = Store.past(this)
        val (value, target) = values(Store.events(this), now, ZoneId.systemDefault(), past)
        Store.tappedAt(this).takeIf { it > 0 }?.let {
            Log.i(TAG, "$label past=$past sent ${now - it} ms after the tap")
        }
        return data(value, target, tapAction())
    }

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        if (type == ComplicationType.GOAL_PROGRESS) data(0f, 1f, null) else null

    // The data slots cover the whole face, so a tap anywhere on it lands here
    // and switches between the coming and the past view.
    private fun tapAction(): PendingIntent = PendingIntent.getBroadcast(
        this, 0, Intent(this, TapReceiver::class.java), PendingIntent.FLAG_IMMUTABLE,
    )

    // GOAL_PROGRESS data must carry a text, title or image; the watch face
    // ignores it and only reads the two numbers.
    private fun data(value: Float, target: Float, tap: PendingIntent?): ComplicationData {
        val text = PlainComplicationText.Builder(label).build()
        return GoalProgressComplicationData.Builder(value, target, text)
            .setText(text)
            .setTapAction(tap)
            .build()
    }

    companion object {
        const val TAG = "Rings"
    }
}

class HourRingDataSource : RingDataSource() {
    override val label = "Rings hour"
    override fun values(events: LongArray, now: Long, zone: ZoneId, past: Boolean) =
        Rings.hourRing(events, now, zone, past)
}

class WeekADataSource : RingDataSource() {
    override val label = "Rings week A"
    override fun values(events: LongArray, now: Long, zone: ZoneId, past: Boolean) =
        Rings.weekA(Rings.weekMasks(events, now, zone, past))
}

class WeekBDataSource : RingDataSource() {
    override val label = "Rings week B"
    override fun values(events: LongArray, now: Long, zone: ZoneId, past: Boolean) =
        Rings.weekB(Rings.weekMasks(events, now, zone, past))
}

class MinuteRingDataSource : RingDataSource() {
    override val label = "Rings minute"
    override fun values(events: LongArray, now: Long, zone: ZoneId, past: Boolean) =
        Rings.minuteRing(events, now, zone, past)
}
