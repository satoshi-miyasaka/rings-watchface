package io.github.satoshimiyasaka.rings

import android.Manifest
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.provider.CalendarContract
import androidx.core.content.ContextCompat
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.tasks.await
import java.util.concurrent.TimeUnit

/** Shared with the wear module: where the event list lives in the Data Layer. */
const val EVENTS_PATH = "/rings/events"
const val KEY_EVENTS = "events"
const val KEY_SYNCED_AT = "synced_at"

/**
 * Reads the coming week of events from the phone's calendars and sends their
 * start and end times to the watch. Titles and other details stay on the phone.
 */
object EventSync {

    // The watch's week ring covers 7 days ahead; one extra day absorbs time
    // zone differences and the gap until the next sync.
    private val WINDOW_MS = TimeUnit.DAYS.toMillis(8)

    fun hasPermission(context: Context) =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CALENDAR) ==
            PackageManager.PERMISSION_GRANTED

    /** Returns start/end pairs flattened as [start0, end0, start1, end1, ...]. */
    fun readEvents(context: Context, now: Long = System.currentTimeMillis()): LongArray {
        if (!hasPermission(context)) return LongArray(0)
        val uri = CalendarContract.Instances.CONTENT_URI.buildUpon().also {
            ContentUris.appendId(it, now)
            ContentUris.appendId(it, now + WINDOW_MS)
        }.build()
        val projection = arrayOf(
            CalendarContract.Instances.BEGIN,
            CalendarContract.Instances.END,
        )
        // All-day events (birthdays, holidays, trips) would fill whole days, and
        // declined invitations are not plans; leave both out.
        val selection = "${CalendarContract.Instances.ALL_DAY} = 0" +
            " AND ${CalendarContract.Instances.VISIBLE} = 1" +
            " AND ${CalendarContract.Instances.SELF_ATTENDEE_STATUS} != " +
            CalendarContract.Attendees.ATTENDEE_STATUS_DECLINED
        val out = ArrayList<Long>()
        context.contentResolver.query(uri, projection, selection, null, null)?.use { c ->
            while (c.moveToNext()) {
                val begin = c.getLong(0)
                val end = c.getLong(1)
                if (end > now && end > begin) {
                    out += begin
                    out += end
                }
            }
        }
        return out.toLongArray()
    }

    /** Sends the events to every connected watch; returns how many were sent. */
    suspend fun sync(context: Context): Int {
        val events = readEvents(context)
        val request = PutDataMapRequest.create(EVENTS_PATH).apply {
            dataMap.putLongArray(KEY_EVENTS, events)
            // Changes every time, so the watch hears about each sync even
            // when the event list is unchanged.
            dataMap.putLong(KEY_SYNCED_AT, System.currentTimeMillis())
        }.asPutDataRequest().setUrgent()
        Wearable.getDataClient(context).putDataItem(request).await()
        context.getSharedPreferences("sync", Context.MODE_PRIVATE).edit()
            .putLong(KEY_SYNCED_AT, System.currentTimeMillis())
            .putInt("count", events.size / 2)
            .apply()
        return events.size / 2
    }
}
