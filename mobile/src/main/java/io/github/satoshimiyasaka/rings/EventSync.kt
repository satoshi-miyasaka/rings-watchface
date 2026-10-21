package io.github.satoshimiyasaka.rings

import android.Manifest
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.database.Cursor
import android.os.BatteryManager
import android.provider.CalendarContract
import androidx.core.content.ContextCompat
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.tasks.await
import java.util.concurrent.TimeUnit

/** Shared with the wear module: where the event list lives in the Data Layer. */
const val EVENTS_PATH = "/rings/events"
const val KEY_EVENTS = "events"
const val KEY_DAYS_OFF = "days_off"
const val KEY_ALL_DAY = "all_day"
const val KEY_PHONE_BATTERY = "phone_battery"
const val KEY_SYNCED_AT = "synced_at"
const val KEY_MODE = "mode"
const val MODE_PER_LAP = 0
const val MODE_EVERY_FIVE_MINUTES = 1

/** A calendar on the phone, as offered in the app. */
class CalendarInfo(val id: Long, val name: String, val account: String)

/**
 * Reads today's and the coming week's events from the chosen calendars and
 * sends their start and end times to the watch, with the days off, the days
 * with other all-day events, the switching mode and the phone's battery.
 * Titles and other details stay on the phone.
 */
object EventSync {

    // The watch's week ring covers today and the coming six days, keeping
    // today's passed hours; one extra day each way absorbs time zone
    // differences and the gap until the next sync.
    private val WINDOW_MS = TimeUnit.DAYS.toMillis(8)
    private val PAST_MS = TimeUnit.DAYS.toMillis(1)
    private val DAY_MS = TimeUnit.DAYS.toMillis(1)

    fun hasPermission(context: Context) =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CALENDAR) ==
            PackageManager.PERMISSION_GRANTED

    fun calendars(context: Context): List<CalendarInfo> {
        if (!hasPermission(context)) return emptyList()
        val projection = arrayOf(
            CalendarContract.Calendars._ID,
            CalendarContract.Calendars.CALENDAR_DISPLAY_NAME,
            CalendarContract.Calendars.ACCOUNT_NAME,
        )
        val out = ArrayList<CalendarInfo>()
        context.contentResolver.query(
            CalendarContract.Calendars.CONTENT_URI, projection, null, null,
            "${CalendarContract.Calendars.ACCOUNT_NAME}, ${CalendarContract.Calendars.CALENDAR_DISPLAY_NAME}",
        )?.use { c ->
            while (c.moveToNext()) out += CalendarInfo(c.getLong(0), c.getString(1).orEmpty(), c.getString(2).orEmpty())
        }
        return out
    }

    private fun query(
        context: Context, now: Long, allDay: Boolean, projection: Array<String>, row: (Cursor) -> Unit,
    ) {
        if (!hasPermission(context)) return
        val uri = CalendarContract.Instances.CONTENT_URI.buildUpon().also {
            ContentUris.appendId(it, now - PAST_MS)
            ContentUris.appendId(it, now + WINDOW_MS)
        }.build()
        // Declined invitations are not plans, and hidden or switched-off calendars are left out.
        val excluded = Settings.excludedCalendars(context)
        val selection = "${CalendarContract.Instances.ALL_DAY} = ${if (allDay) 1 else 0}" +
            " AND ${CalendarContract.Instances.VISIBLE} = 1" +
            " AND ${CalendarContract.Instances.SELF_ATTENDEE_STATUS} != " +
            CalendarContract.Attendees.ATTENDEE_STATUS_DECLINED +
            if (excluded.isEmpty()) "" else
                " AND ${CalendarContract.Instances.CALENDAR_ID} NOT IN (${excluded.joinToString(",")})"
        context.contentResolver.query(uri, projection, selection, null, null)?.use { c ->
            while (c.moveToNext()) row(c)
        }
    }

    /**
     * Returns start/end pairs flattened as [start0, end0, start1, end1, ...].
     * All-day events would fill whole days, so they travel as days instead; see [readAllDay].
     */
    fun readEvents(context: Context, now: Long = System.currentTimeMillis()): LongArray {
        val out = ArrayList<Long>()
        val projection = arrayOf(CalendarContract.Instances.BEGIN, CalendarContract.Instances.END)
        query(context, now, allDay = false, projection) { c ->
            val begin = c.getLong(0)
            val end = c.getLong(1)
            if (end > now - PAST_MS && end > begin) {
                out += begin
                out += end
            }
        }
        return out.toLongArray()
    }

    /**
     * Epoch days of all-day events: first the days off, whose title has one of
     * the day-off words such as 有給, then the days with any other all-day event.
     */
    fun readAllDay(context: Context, now: Long = System.currentTimeMillis()): Pair<LongArray, LongArray> {
        val words = Settings.dayOffWords(context)
        val daysOff = sortedSetOf<Long>()
        val others = sortedSetOf<Long>()
        val projection = arrayOf(
            CalendarContract.Instances.TITLE,
            CalendarContract.Instances.BEGIN,
            CalendarContract.Instances.END,
        )
        query(context, now, allDay = true, projection) { c ->
            val title = c.getString(0).orEmpty()
            val days = if (words.any { title.contains(it) }) daysOff else others
            // All-day events run from midnight to midnight UTC.
            val first = Math.floorDiv(c.getLong(1), DAY_MS)
            val last = Math.floorDiv(c.getLong(2) - 1, DAY_MS)
            for (day in first..last) days += day
        }
        return daysOff.toLongArray() to others.toLongArray()
    }

    /** The phone's battery in percent, or -1 if unknown. */
    private fun battery(context: Context): Int {
        val level = context.getSystemService(BatteryManager::class.java)
            ?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: -1
        return if (level in 0..100) level else -1
    }

    /** Sends the events and settings to every connected watch; returns how many events were sent. */
    suspend fun sync(context: Context): Int {
        val events = readEvents(context)
        val now = System.currentTimeMillis()
        val request = PutDataMapRequest.create(EVENTS_PATH).apply {
            dataMap.putLongArray(KEY_EVENTS, events)
            val (daysOff, allDay) = readAllDay(context)
            dataMap.putLongArray(KEY_DAYS_OFF, daysOff)
            dataMap.putLongArray(KEY_ALL_DAY, allDay)
            dataMap.putInt(KEY_PHONE_BATTERY, battery(context))
            dataMap.putInt(KEY_MODE, Settings.mode(context))
            // Changes every time, so the watch hears about each sync even
            // when nothing else changed.
            dataMap.putLong(KEY_SYNCED_AT, now)
        }.asPutDataRequest().setUrgent()
        Wearable.getDataClient(context).putDataItem(request).await()
        context.getSharedPreferences("sync", Context.MODE_PRIVATE).edit()
            .putLong(KEY_SYNCED_AT, now)
            .putInt("count", events.size / 2)
            .apply()
        return events.size / 2
    }
}
