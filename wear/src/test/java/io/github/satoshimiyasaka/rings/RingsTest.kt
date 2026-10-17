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
    fun hourRingShowsThisHalfOfTheDay() {
        val events = longArrayOf(
            ms(2026, 10, 16, 9, 0), ms(2026, 10, 16, 10, 0), // passed this morning: bits 18, 19
            ms(2026, 10, 16, 1, 0), ms(2026, 10, 16, 1, 30), // 1 o'clock last night: bit 2
            ms(2026, 10, 16, 13, 0), ms(2026, 10, 16, 14, 0), // this afternoon: next lap, not shown
            ms(2026, 10, 15, 23, 0), ms(2026, 10, 16, 0, 0), // yesterday: not shown
        )
        val mask = Rings.hourMask(events, now, tokyo)
        assertEquals((1 shl 18) or (1 shl 19) or (1 shl 2), mask)
    }

    @Test
    fun hourRingMovesToTheAfternoonAtNoon() {
        val events = longArrayOf(
            ms(2026, 10, 16, 9, 0), ms(2026, 10, 16, 10, 0), // this morning: gone
            ms(2026, 10, 16, 13, 0), ms(2026, 10, 16, 14, 0), // 1 o'clock: bits 2, 3
        )
        val mask = Rings.hourMask(events, ms(2026, 10, 16, 12, 0), tokyo)
        assertEquals((1 shl 2) or (1 shl 3), mask)
    }

    @Test
    fun weekRingShowsTodayAndTheComingSixDays() {
        val events = longArrayOf(
            ms(2026, 10, 16, 6, 0), ms(2026, 10, 16, 7, 0), // this morning: Friday block 3 stays
            ms(2026, 10, 16, 15, 0), ms(2026, 10, 16, 16, 0), // this afternoon: Friday block 7
            ms(2026, 10, 19, 10, 0), ms(2026, 10, 19, 11, 0), // Monday 10:00: block 5
            ms(2026, 10, 22, 10, 0), ms(2026, 10, 22, 11, 0), // next Thursday: block 5
            ms(2026, 10, 15, 8, 0), ms(2026, 10, 15, 9, 0), // yesterday: gone
            ms(2026, 10, 23, 8, 0), ms(2026, 10, 23, 9, 0), // next Friday: not until Friday comes round
        )
        val m = Rings.weekMasks(events, now, tokyo)
        assertEquals((1 shl 3) or (1 shl 7), m[5])
        assertEquals(1 shl 5, m[1])
        assertEquals(1 shl 5, m[4])
        assertEquals(0, m[0] or m[2] or m[3] or m[6])
    }

    @Test
    fun weekRingMovesOnAtMidnight() {
        val events = longArrayOf(ms(2026, 10, 16, 6, 0), ms(2026, 10, 16, 7, 0))
        val m = Rings.weekMasks(events, ms(2026, 10, 17, 0, 0), tokyo)
        assertEquals(0, m.reduce { a, b -> a or b })
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
    fun minuteRingShowsThisHour() {
        val events = longArrayOf(
            ms(2026, 10, 16, 11, 0), ms(2026, 10, 16, 11, 3), // passed: minutes 0-2 stay
            ms(2026, 10, 16, 11, 30), ms(2026, 10, 16, 11, 45), // minutes 30-44
            ms(2026, 10, 16, 12, 5), ms(2026, 10, 16, 12, 7), // next hour: not shown
            ms(2026, 10, 16, 10, 50), ms(2026, 10, 16, 10, 52), // last hour: not shown
        )
        var expected = 0L
        for (k in (0..2) + (30..44)) expected = expected or (1L shl k)
        assertEquals(expected, Rings.minuteMask(events, now, tokyo))
    }

    @Test
    fun minuteBitsSplitAcrossTwoSources() {
        val events = longArrayOf(ms(2026, 10, 16, 11, 0), ms(2026, 10, 16, 12, 0))
        val (_, low) = Rings.hourRing(events, now, tokyo)
        val (mid, high) = Rings.minuteRing(events, now, tokyo)
        assertEquals(16_777_216f, low) // bits 0-23 all set, plus one
        assertEquals(16_777_215f, mid) // bits 24-47
        assertEquals(4096f, high) // bits 48-59, plus one
    }
}
