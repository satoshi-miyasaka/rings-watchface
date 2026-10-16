package io.github.satoshimiyasaka.rings

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime

/** Shared with the mobile module: where the event list lives in the Data Layer. */
const val EVENTS_PATH = "/rings/events"
const val KEY_EVENTS = "events"

/**
 * Packs the coming events into numbers for the watch face.
 *
 * A watch face can only read complication data, so each ring's lit segments
 * travel as bits inside GOAL_PROGRESS values. Each value stays at or below
 * 2^24 so that it survives the trip through a 32-bit float exactly.
 *
 * - Hour ring: 24 half-hour segments of the 12-hour dial, bit i = the segment
 *   starting at i * 30 minutes past 12 o'clock. Each segment means its next
 *   occurrence that has not ended yet, so the ring always shows the coming 12
 *   hours and a segment the hand has passed already shows the next lap.
 * - Week ring: 7 weekdays (Sunday = 0) x 12 two-hour blocks, again the next
 *   occurrence of each block.
 * - Minute ring: 60 one-minute segments of the hour, bit k = minute k past the
 *   hour, again the next occurrence that has not ended, so the ring shows the
 *   coming 60 minutes. Bits 0-23 ride on the hour source's target, bits 24-59
 *   on the minute source.
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
        val today = Instant.ofEpochMilli(now).atZone(zone).toLocalDate()
        var mask = 0
        for (i in 0 until HOUR_SEGMENTS) {
            // Candidates at this dial position: yesterday evening through tomorrow.
            for (lap in -2..3) {
                val start = at(today, lap * 12 * 60L + i * HALF_HOUR_MIN, zone)
                val end = start.plusMinutes(HALF_HOUR_MIN)
                if (end.toEpochMilli() <= now) continue
                if (busy(events, start.toEpochMilli(), end.toEpochMilli())) mask = mask or (1 shl i)
                break
            }
        }
        return mask
    }

    fun minuteMask(events: LongArray, now: Long, zone: ZoneId): Long {
        val hour = Instant.ofEpochMilli(now).atZone(zone).withMinute(0).withSecond(0).withNano(0)
        var mask = 0L
        for (k in 0 until MINUTE_SEGMENTS) {
            var start = hour.plusMinutes(k.toLong())
            if (start.plusMinutes(1).toEpochMilli() <= now) start = start.plusHours(1)
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
                var start = at(date, b * BLOCK_MIN, zone)
                if (start.plusMinutes(BLOCK_MIN).toEpochMilli() <= now) start = start.plusDays(7)
                val end = start.plusMinutes(BLOCK_MIN)
                if (busy(events, start.toEpochMilli(), end.toEpochMilli())) mask = mask or (1 shl b)
            }
            mask
        }
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
