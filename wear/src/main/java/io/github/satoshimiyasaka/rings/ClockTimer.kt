package io.github.satoshimiyasaka.rings

/** Reads the end time of a running timer from the watch's Clock app notifications. */
object ClockTimer {
    const val CLOCK_PACKAGE = "com.google.android.deskclock"

    /** What a notification says about a timer; a paused timer shows no countdown. */
    data class Shown(val pkg: String, val countDown: Boolean, val showChronometer: Boolean, val `when`: Long)

    /** The earliest end of a running Clock timer, or 0 when none is running. */
    fun end(shown: List<Shown>, now: Long): Long =
        shown.filter { it.pkg == CLOCK_PACKAGE && it.countDown && it.showChronometer && it.`when` > now }
            .minOfOrNull { it.`when` } ?: 0L
}
