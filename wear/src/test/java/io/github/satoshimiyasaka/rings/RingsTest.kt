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
    fun timerEndsAsSecondOfDay() {
        val end = ms(2026, 10, 16, 11, 25)
        assertEquals((11 * 3600 + 25 * 60 + 1).toFloat(), Rings.timerValue(end, now, tokyo))
        assertEquals(Rings.NO_TIMER, Rings.timerValue(now - 1, now, tokyo))
    }
}
