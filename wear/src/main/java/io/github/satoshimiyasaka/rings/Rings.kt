package io.github.satoshimiyasaka.rings

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime

/** Shared with the mobile module: where the event list lives in the Data Layer. */
const val EVENTS_PATH = "/rings/events"
const val KEY_EVENTS = "events"

/**
 * Packs the events into numbers for the watch face.
 *
 * A watch face can only read complication data, so each ring's lit segments
 * travel as bits inside GOAL_PROGRESS values. Each value stays at or below
 * 2^24 so that it survives the trip through a 32-bit float exactly.
 *
 * Each ring shows the lap its hand is on and moves to the next lap all at
 * once when the hand completes it, so segments the hand has passed keep
 * showing this lap's events.
 *
 * - Hour ring: 24 half-hour segments of the 12-hour dial, bit i = the segment
 *   starting at i * 30 minutes after 0:00 or 12:00, whichever half of the day
 *   it is now.
 * - Week ring: 7 weekdays (Sunday = 0) x 12 two-hour blocks. Today's weekday
 *   holds today, and the others the coming six days; it moves on at 0:00.
 * - Minute ring: 60 one-minute segments of the current clock hour, bit k =
 *   minute k. Bits 0-23 ride on the hour source's target, bits 24-59 on the
 *   minute source.
 * - A target is never 0, so each one carries its bits plus one.
 *
 * The watch face side lives in tools/generate_watchface.py.
 */
object Rings {
    const val HOUR_SEGMENTS = 24
    const val WEEK_BLOCKS = 12
    const val MINUTE_SEGMENTS = 60

    private const val HALF_HOUR_MIN = 30L
    private const val BLOCK_MIN = 120L

    /** True if any [start, end) pair in [events] overlaps [from, to). */
    fun busy(events: LongArray, from: Long, to: Long): Boolean {
        var i = 0
        while (i + 1 < events.size) {
            if (events[i] < to && events[i + 1] > from) return true
            i += 2
        }
        return false
    }

    fun hourMask(events: LongArray, now: Long, zone: ZoneId): Int {
        val time = Instant.ofEpochMilli(now).atZone(zone)
        val lapStart = if (time.hour < 12) 0L else 12 * 60L
        var mask = 0
        for (i in 0 until HOUR_SEGMENTS) {
            val start = at(time.toLocalDate(), lapStart + i * HALF_HOUR_MIN, zone)
            val end = start.plusMinutes(HALF_HOUR_MIN)
            if (busy(events, start.toEpochMilli(), end.toEpochMilli())) mask = mask or (1 shl i)
        }
        return mask
    }

    fun minuteMask(events: LongArray, now: Long, zone: ZoneId): Long {
        val hour = Instant.ofEpochMilli(now).atZone(zone).withMinute(0).withSecond(0).withNano(0)
        var mask = 0L
        for (k in 0 until MINUTE_SEGMENTS) {
            val start = hour.plusMinutes(k.toLong())
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

    /**
     * When the rings may change over the coming [hours]: now, then every top
     * of the hour, which covers the minute ring's hourly lap and the hour and
     * week rings' changes at 0:00 and 12:00. The last time ends the timeline.
     */
    fun switchTimes(now: Long, zone: ZoneId, hours: Int = 24): List<Long> {
        val hour = Instant.ofEpochMilli(now).atZone(zone).withMinute(0).withSecond(0).withNano(0)
        return listOf(now) + (1..hours).map { hour.plusHours(it.toLong()).toEpochMilli() }
    }

    /** Values for the four data sources: (value, target) each. */
    fun hourRing(events: LongArray, now: Long, zone: ZoneId) =
        hourMask(events, now, zone).toFloat() to
            ((minuteMask(events, now, zone) and 0xFFFFFF).toInt() + 1).toFloat()

    fun minuteRing(events: LongArray, now: Long, zone: ZoneId): Pair<Float, Float> {
        val m = minuteMask(events, now, zone)
        return ((m shr 24) and 0xFFFFFF).toFloat() to (((m shr 48) and 0xFFF).toInt() + 1).toFloat()
    }

    fun weekA(m: IntArray) =
        (m[0] or (m[1] shl 12)).toFloat() to ((m[2] or (m[3] shl 12)) + 1).toFloat()

    fun weekB(m: IntArray) =
        (m[4] or (m[5] shl 12)).toFloat() to (m[6] + 1).toFloat()

    private fun at(date: LocalDate, minutes: Long, zone: ZoneId): ZonedDateTime =
        date.atStartOfDay(zone).plusMinutes(minutes)

    private fun ZonedDateTime.toEpochMilli() = toInstant().toEpochMilli()
}
