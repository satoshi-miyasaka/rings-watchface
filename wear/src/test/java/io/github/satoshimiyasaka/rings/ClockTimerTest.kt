package io.github.satoshimiyasaka.rings

import org.junit.Assert.assertEquals
import org.junit.Test

class ClockTimerTest {
    private val now = 1_792_130_139_505L
    private fun clock(end: Long, countDown: Boolean = true, shown: Boolean = true) =
        ClockTimer.Shown(ClockTimer.CLOCK_PACKAGE, countDown, shown, end)

    @Test
    fun runningTimerGivesItsEnd() {
        assertEquals(now + 300_000, ClockTimer.end(listOf(clock(now + 300_000)), now))
    }

    @Test
    fun earliestOfSeveralTimersWins() {
        assertEquals(now + 60_000, ClockTimer.end(listOf(clock(now + 300_000), clock(now + 60_000)), now))
    }

    @Test
    fun pausedEndedOrOtherNotificationsAreIgnored() {
        val shown = listOf(
            clock(now + 300_000, shown = false),
            clock(now + 300_000, countDown = false),
            clock(now - 1),
            ClockTimer.Shown("com.example", true, true, now + 300_000),
        )
        assertEquals(0L, ClockTimer.end(shown, now))
    }
}
