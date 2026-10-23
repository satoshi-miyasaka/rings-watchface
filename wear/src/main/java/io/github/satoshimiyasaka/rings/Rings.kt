package io.github.satoshimiyasaka.rings

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime

/** Shared with the mobile module: where the event list lives in the Data Layer. */
const val EVENTS_PATH = "/rings/events"
const val KEY_EVENTS = "events"
const val KEY_DAYS_OFF = "days_off"
const val KEY_ALL_DAY = "all_day"
const val KEY_PHONE_BATTERY = "phone_battery"
const val KEY_SYNCED_AT = "synced_at"
const val KEY_MODE = "mode"
const val MODE_PER_LAP = 0
const val MODE_EVERY_FIVE_MINUTES = 1

/** Everything the phone sends, as kept on the watch. */
class Inputs(
    /** Start/end pairs flattened as [start0, end0, start1, end1, ...]. */
    val events: LongArray,
    /** Days off found in the phone's calendar, as epoch days. */
    val daysOff: LongArray = LongArray(0),
    /** Days with other all-day events, as epoch days. */
    val allDay: LongArray = LongArray(0),
    /** The phone's battery in percent at [syncedAt], or -1. */
    val phoneBattery: Int = -1,
    val syncedAt: Long = 0,
    val mode: Int = MODE_PER_LAP,
)

/**
 * Packs the events into numbers for the watch face.
 *
 * A watch face can only read complication data, so each ring's lit segments
 * travel as bits inside GOAL_PROGRESS values. Each value stays at or below
 * 2^24 so that it survives the trip through a 32-bit float exactly.
 *
 * The hour and minute rings switch in one of two modes. Per lap, a ring shows
 * the lap its hand is on and moves to the next lap all at once when the hand
 * completes it, so segments the hand has passed keep showing this lap's
 * events. Every five minutes, segments the hand has passed show the next lap
 * instead, updated every five minutes. The week ring always switches at 0:00.
 *
 * - Hour ring: 12 one-hour segments of the 12-hour dial, bit i = the segment
 *   starting at i hours after 0:00 or 12:00, whichever half of the day
 *   it is now.
 * - Week ring: 7 weekdays (Sunday = 0) x 12 two-hour blocks. Today's weekday
 *   holds today, and the others the coming six days; it moves on at 0:00.
 * - Minute ring: 60 one-minute segments of the current clock hour, bit k =
 *   minute k. Bits 0-23 ride on the hour source's target, bits 24-59 on the
 *   minute source.
 * - Days off: week B's target bits 12-18, one per weekday (Sunday = 0), for
 *   the same days as the week ring.
 * - Phone battery: the minute source's target bits 12-18 hold the percentage
 *   and bit 19 says it is fresh.
 * - Days with other all-day events: Sunday to Thursday on week B's target
 *   bits 19-23, Friday and Saturday on the minute source's target bits 20-21.
 * - A target is never 0, so each one carries its bits plus one.
 *
 * The watch face side lives in tools/generate_watchface.py.
 */
object Rings {
    const val HOUR_SEGMENTS = 12
    const val WEEK_BLOCKS = 12
    const val MINUTE_SEGMENTS = 60

    private const val HOUR_MIN = 60L
    private const val BLOCK_MIN = 120L

    // The phone syncs hourly; past this its battery reading is left off the ring.
    private const val BATTERY_FRESH_MS = 3 * 60 * 60 * 1000L

    /** True if any [start, end) pair in [events] overlaps [from, to). */
    fun busy(events: LongArray, from: Long, to: Long): Boolean {
        var i = 0
        while (i + 1 < events.size) {
            if (events[i] < to && events[i + 1] > from) return true
            i += 2
        }
        return false
    }

    /** With [rolling], segments that have ended show the next lap. */
    fun hourMask(events: LongArray, now: Long, zone: ZoneId, rolling: Boolean = false): Int {
        val time = Instant.ofEpochMilli(now).atZone(zone)
        val lapStart = if (time.hour < 12) 0L else 12 * 60L
        var mask = 0
        for (i in 0 until HOUR_SEGMENTS) {
            var start = at(time.toLocalDate(), lapStart + i * HOUR_MIN, zone)
            if (rolling && start.plusMinutes(HOUR_MIN).toEpochMilli() <= now) start = start.plusHours(12)
            val end = start.plusMinutes(HOUR_MIN)
            if (busy(events, start.toEpochMilli(), end.toEpochMilli())) mask = mask or (1 shl i)
        }
        return mask
    }

    fun minuteMask(events: LongArray, now: Long, zone: ZoneId, rolling: Boolean = false): Long {
        val hour = Instant.ofEpochMilli(now).atZone(zone).withMinute(0).withSecond(0).withNano(0)
        var mask = 0L
        for (k in 0 until MINUTE_SEGMENTS) {
            var start = hour.plusMinutes(k.toLong())
            if (rolling && start.plusMinutes(1).toEpochMilli() <= now) start = start.plusHours(1)
            if (busy(events, start.toEpochMilli(), start.plusMinutes(1).toEpochMilli())) mask = mask or (1L shl k)
        }
        return mask
    }

    /** One 12-bit mask per weekday, Sunday first. */
    fun weekMasks(events: LongArray, now: Long, zone: ZoneId): IntArray {
        val today = Instant.ofEpochMilli(now).atZone(zone).toLocalDate()
        val todayIndex = today.dayOfWeek.value % 7 // Monday = 1 ... Sunday = 0
        return IntArray(7) { day ->
            val date = today.plusDays(((day - todayIndex + 7) % 7).toLong())
            var mask = 0
            for (b in 0 until WEEK_BLOCKS) {
                val start = at(date, b * BLOCK_MIN, zone)
                val end = start.plusMinutes(BLOCK_MIN)
                if (busy(events, start.toEpochMilli(), end.toEpochMilli())) mask = mask or (1 shl b)
            }
            mask
        }
    }

    /** One bit per weekday, Sunday first, for the days off among the week ring's days. */
    fun daysOffFlags(daysOff: LongArray, now: Long, zone: ZoneId): Int {
        val today = Instant.ofEpochMilli(now).atZone(zone).toLocalDate()
        var flags = 0
        for (i in 0L until 7L) {
            val date = today.plusDays(i)
            if (date.toEpochDay() in daysOff) flags = flags or (1 shl (date.dayOfWeek.value % 7))
        }
        return flags
    }

    /** The phone's battery and a fresh flag (bit 7), or 0 once the last sync is too old. */
    fun phoneBatteryBits(battery: Int, syncedAt: Long, now: Long): Int =
        if (battery in 0..100 && now - syncedAt in 0 until BATTERY_FRESH_MS) battery or (1 shl 7) else 0

    /**
     * When the rings may change over the coming [hours]: now, then every
     * [stepMinutes] on the clock. Steps of an hour cover the minute ring's
     * hourly lap and the hour and week rings' changes at 0:00 and 12:00. The
     * last time ends the timeline.
     */
    fun switchTimes(now: Long, zone: ZoneId, hours: Int = 24, stepMinutes: Long = 60): List<Long> {
        val hour = Instant.ofEpochMilli(now).atZone(zone).withMinute(0).withSecond(0).withNano(0)
        val first = generateSequence(hour) { it.plusMinutes(stepMinutes) }.first { it.toEpochMilli() > now }
        val steps = hours * 60L / stepMinutes
        return listOf(now) + (0L until steps).map { first.plusMinutes(it * stepMinutes).toEpochMilli() }
    }

    /** Values for the four data sources: (value, target) each. */
    fun hourRing(events: LongArray, now: Long, zone: ZoneId, rolling: Boolean = false) =
        hourMask(events, now, zone, rolling).toFloat() to
            ((minuteMask(events, now, zone, rolling) and 0xFFFFFF).toInt() + 1).toFloat()

    fun minuteRing(
        events: LongArray, now: Long, zone: ZoneId, rolling: Boolean = false, phoneBattery: Int = 0,
        allDay: Int = 0,
    ): Pair<Float, Float> {
        val m = minuteMask(events, now, zone, rolling)
        val high = ((m shr 48) and 0xFFF).toInt() or (phoneBattery shl 12) or ((allDay shr 5) shl 20)
        return ((m shr 24) and 0xFFFFFF).toFloat() to (high + 1).toFloat()
    }

    fun weekA(m: IntArray) =
        (m[0] or (m[1] shl 12)).toFloat() to ((m[2] or (m[3] shl 12)) + 1).toFloat()

    fun weekB(m: IntArray, daysOff: Int = 0, allDay: Int = 0) =
        (m[4] or (m[5] shl 12)).toFloat() to
            ((m[6] or (daysOff shl 12) or ((allDay and 0x1F) shl 19)) + 1).toFloat()

    /** Weekday bits for days with all-day events, leaving out the days off. */
    fun allDayFlags(inputs: Inputs, now: Long, zone: ZoneId): Int =
        daysOffFlags(inputs.allDay, now, zone) and daysOffFlags(inputs.daysOff, now, zone).inv()

    private fun at(date: LocalDate, minutes: Long, zone: ZoneId): ZonedDateTime =
        date.atStartOfDay(zone).plusMinutes(minutes)

    private fun ZonedDateTime.toEpochMilli() = toInstant().toEpochMilli()
}
