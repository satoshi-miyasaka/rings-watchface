package io.github.satoshimiyasaka.rings

import android.content.Context

/** What the person chose in the phone app. */
object Settings {
    /** Words that make an all-day event a day off, unless changed. */
    const val DEFAULT_DAY_OFF_WORDS = "休み,休暇,有給,休日"

    private fun prefs(context: Context) =
        context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    /** Calendars left out; new calendars are included until switched off. */
    fun excludedCalendars(context: Context): Set<Long> =
        prefs(context).getStringSet("excluded_calendars", emptySet())!!.map { it.toLong() }.toSet()

    fun setCalendarIncluded(context: Context, id: Long, included: Boolean) {
        val ids = excludedCalendars(context).let { if (included) it - id else it + id }
        prefs(context).edit().putStringSet("excluded_calendars", ids.map { it.toString() }.toSet()).apply()
    }

    fun mode(context: Context): Int = prefs(context).getInt("mode", MODE_PER_LAP)

    fun setMode(context: Context, mode: Int) = prefs(context).edit().putInt("mode", mode).apply()

    fun dayOffWordsText(context: Context): String =
        prefs(context).getString("day_off_words", DEFAULT_DAY_OFF_WORDS)!!

    fun dayOffWords(context: Context): List<String> =
        dayOffWordsText(context).split(',', '、').map { it.trim() }.filter { it.isNotEmpty() }

    fun setDayOffWords(context: Context, text: String) =
        prefs(context).edit().putString("day_off_words", text).apply()
}
