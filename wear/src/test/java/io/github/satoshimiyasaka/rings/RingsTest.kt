package io.github.satoshimiyasaka.rings

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.ZoneId
import java.time.ZonedDateTime

class RingsTest {
    private val tokyo = ZoneId.of("Asia/Tokyo")

    // Friday 16 October 2026, 11:10 in Tokyo.
    private val now = ms(2026, 10, 16, 11, 10)

    private fun ms(y: Int, mo: Int, d: Int, h: Int, mi: Int) =
        ZonedDateTime.of(y, mo, d, h, mi, 0, 0, tokyo).toInstant().toEpochMilli()

    @Test
    fun hourRingShowsTheComingTwelveHours() {
        val events = longArrayOf(
            ms(2026, 10, 16, 13, 0), ms(2026, 10, 16, 14, 0), // 1 o'clock: bits 2, 3
            ms(2026, 10, 16, 9, 0), ms(2026, 10, 16, 10, 0), // passed: not shown
            ms(2026, 10, 16, 21, 30), ms(2026, 10, 16, 22, 0), // 9:30 tonight: bit 19
            ms(2026, 10, 17, 2, 0), ms(2026, 10, 17, 3, 0), // beyond 12 hours: not shown
        )
        val mask = Rings.hourMask(events, now, tokyo)
        assertEquals((1 shl 2) or (1 shl 3) or (1 shl 19), mask)
    }

    @Test
    fun passedSegmentShowsTheNextLap() {
        // 9:00-9:30 tonight sits where this morning's 9:00 segment already passed.
        val events = longArrayOf(ms(2026, 10, 16, 21, 0), ms(2026, 10, 16, 21, 30))
        assertEquals(1 shl 18, Rings.hourMask(events, now, tokyo))
    }

    @Test
    fun currentSegmentStaysWhileRunning() {
        // 11:00-11:30 is under way at 11:10.
        val events = longArrayOf(ms(2026, 10, 16, 11, 0), ms(2026, 10, 16, 11, 30))
        assertEquals(1 shl 22, Rings.hourMask(events, now, tokyo))
    }

    @Test
    fun weekRingUsesNextOccurrenceOfEachBlock() {
        val events = longArrayOf(
            ms(2026, 10, 19, 10, 0), ms(2026, 10, 19, 11, 0), // Monday 10:00: block 5
            ms(2026, 10, 16, 15, 0), ms(2026, 10, 16, 16, 0), // today 15:00: block 7
            ms(2026, 10, 23, 8, 0), ms(2026, 10, 23, 9, 0), // next Friday 8:00, block 4 has passed today
            ms(2026, 10, 16, 6, 0), ms(2026, 10, 16, 7, 0), // this morning: gone
        )
        val m = Rings.weekMasks(events, now, tokyo)
        assertEquals(1 shl 5, m[1])
        assertEquals((1 shl 7) or (1 shl 4), m[5])
        assertEquals(0, m[0] or m[2] or m[3] or m[4] or m[6])
    }

    @Test
    fun packedValuesStayExactInAFloat() {
        val all = IntArray(7) { 0xFFF }
        val (a, b) = Rings.weekA(all)
        assertEquals(16_777_215f, a)
        assertEquals(16_777_216f, b)
        assertEquals(16_777_215.0, a.toDouble(), 0.0)
        val (c, d) = Rings.weekB(all)
        assertEquals(16_777_215f, c)
        assertEquals(4096f, d)
    }

    @Test
    fun minuteRingShowsTheComingSixtyMinutes() {
        val events = longArrayOf(
            ms(2026, 10, 16, 11, 30), ms(2026, 10, 16, 11, 45), // minutes 30-44
            ms(2026, 10, 16, 12, 5), ms(2026, 10, 16, 12, 7), // next lap: minutes 5-6
            ms(2026, 10, 16, 11, 0), ms(2026, 10, 16, 11, 3), // passed and not next lap: off
            ms(2026, 10, 16, 12, 20), ms(2026, 10, 16, 12, 30), // beyond 60 minutes: off
        )
        var expected = 0L
        for (k in 30..44) expected = expected or (1L shl k)
        expected = expected or (1L shl 5) or (1L shl 6)
        assertEquals(expected, Rings.minuteMask(events, now, tokyo))
    }

    @Test
    fun currentMinuteStaysWhileRunning() {
        val events = longArrayOf(ms(2026, 10, 16, 11, 0), ms(2026, 10, 16, 11, 11))
        assertEquals(1L shl 10, Rings.minuteMask(events, now, tokyo))
    }

    @Test
    fun minuteBitsSplitAcrossTwoSources() {
        val events = longArrayOf(ms(2026, 10, 16, 11, 10), ms(2026, 10, 16, 12, 10))
        val (_, low) = Rings.hourRing(events, now, tokyo)
        val (mid, high) = Rings.minuteRing(events, now, tokyo)
        assertEquals(16_777_216f, low) // bits 0-23 all set, plus one
        assertEquals(16_777_215f, mid) // bits 24-47
        assertEquals(4096f, high) // bits 48-59, plus one
    }

    @Test
    fun pastHourRingShowsThePastTwelveHours() {
        val events = longArrayOf(
            ms(2026, 10, 16, 10, 0), ms(2026, 10, 16, 10, 30), // this morning: bit 20
            ms(2026, 10, 16, 1, 0), ms(2026, 10, 16, 1, 30), // 1 o'clock last night: bit 2
            ms(2026, 10, 15, 23, 30), ms(2026, 10, 16, 0, 0), // 11:30 last night: bit 23
            ms(2026, 10, 16, 13, 0), ms(2026, 10, 16, 14, 0), // still to come: not shown
        )
        val mask = Rings.hourMask(events, now, tokyo, past = true)
        assertEquals((1 shl 20) or (1 shl 2) or (1 shl 23), mask)
    }

    @Test
    fun pastMinuteRingShowsThePastSixtyMinutes() {
        val events = longArrayOf(
            ms(2026, 10, 16, 11, 5), ms(2026, 10, 16, 11, 7), // minutes 5-6
            ms(2026, 10, 16, 10, 50), ms(2026, 10, 16, 10, 52), // last lap: minutes 50-51
            ms(2026, 10, 16, 11, 9), ms(2026, 10, 16, 11, 12), // 9, and 10 which is under way
            ms(2026, 10, 16, 11, 30), ms(2026, 10, 16, 11, 31), // still to come: off
        )
        val expected = (1L shl 5) or (1L shl 6) or (1L shl 9) or (1L shl 10) or (1L shl 50) or (1L shl 51)
        assertEquals(expected, Rings.minuteMask(events, now, tokyo, past = true))
    }

    @Test
    fun pastWeekRingShowsThePastSevenDays() {
        val events = longArrayOf(
            ms(2026, 10, 15, 10, 0), ms(2026, 10, 15, 11, 0), // yesterday 10:00: Thursday block 5
            ms(2026, 10, 16, 6, 0), ms(2026, 10, 16, 7, 0), // this morning: Friday block 3
            ms(2026, 10, 9, 14, 0), ms(2026, 10, 9, 15, 0), // last Friday 14:00: block 7 has not come today
            ms(2026, 10, 19, 10, 0), ms(2026, 10, 19, 11, 0), // next Monday: not shown
        )
        val m = Rings.weekMasks(events, now, tokyo, past = true)
        assertEquals(1 shl 5, m[4])
        assertEquals((1 shl 3) or (1 shl 7), m[5])
        assertEquals(0, m[0] or m[1] or m[2] or m[3] or m[6])
    }

    @Test
    fun minuteSourceMarksThePastView() {
        val (_, coming) = Rings.minuteRing(LongArray(0), now, tokyo)
        val (_, past) = Rings.minuteRing(LongArray(0), now, tokyo, past = true)
        assertEquals(1f, coming)
        assertEquals((Rings.PAST_FLAG + 1).toFloat(), past)
    }
}
