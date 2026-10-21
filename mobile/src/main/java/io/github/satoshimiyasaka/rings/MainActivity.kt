package io.github.satoshimiyasaka.rings

import android.Manifest
import android.content.Context
import android.os.Bundle
import android.text.format.DateFormat
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioGroup
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Date

class MainActivity : ComponentActivity() {

    private lateinit var status: TextView
    private lateinit var action: Button
    private var pendingSync: Job? = null

    private val requestCalendar =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { render() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)
        action = findViewById(R.id.action)

        val mode = findViewById<RadioGroup>(R.id.mode)
        mode.check(
            if (Settings.mode(this) == MODE_EVERY_FIVE_MINUTES) R.id.mode_five_minutes else R.id.mode_per_lap
        )
        mode.setOnCheckedChangeListener { _, checked ->
            Settings.setMode(this, if (checked == R.id.mode_five_minutes) MODE_EVERY_FIVE_MINUTES else MODE_PER_LAP)
            syncSoon()
        }

        val words = findViewById<EditText>(R.id.day_off_words)
        words.setText(Settings.dayOffWordsText(this))
        words.doAfterTextChanged {
            Settings.setDayOffWords(this, it.toString())
            syncSoon()
        }
    }

    override fun onResume() {
        super.onResume()
        render()
    }

    private fun render() {
        if (!EventSync.hasPermission(this)) {
            status.setText(R.string.status_need_permission)
            action.setText(R.string.grant)
            action.setOnClickListener { requestCalendar.launch(Manifest.permission.READ_CALENDAR) }
            return
        }
        SyncWorker.schedule(this)
        showLastSync()
        action.setText(R.string.sync_now)
        action.setOnClickListener {
            pendingSync?.cancel()
            lifecycleScope.launch { syncNow() }
        }
        findViewById<View>(R.id.settings).visibility = View.VISIBLE
        showCalendars()
    }

    private fun showCalendars() {
        val list = findViewById<LinearLayout>(R.id.calendars)
        list.removeAllViews()
        val excluded = Settings.excludedCalendars(this)
        for (calendar in EventSync.calendars(this)) {
            list.addView(CheckBox(this).apply {
                text = if (calendar.account.isEmpty() || calendar.account == calendar.name) {
                    calendar.name
                } else {
                    "${calendar.name}（${calendar.account}）"
                }
                isChecked = calendar.id !in excluded
                setOnCheckedChangeListener { _, checked ->
                    Settings.setCalendarIncluded(this@MainActivity, calendar.id, checked)
                    syncSoon()
                }
            })
        }
    }

    /** Sends the new settings once the person stops changing them for a moment. */
    private fun syncSoon() {
        if (!EventSync.hasPermission(this)) return
        pendingSync?.cancel()
        pendingSync = lifecycleScope.launch {
            delay(1500)
            syncNow()
        }
    }

    private suspend fun syncNow() {
        action.isEnabled = false
        try {
            EventSync.sync(this)
            showLastSync()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            status.text = e.localizedMessage
        } finally {
            action.isEnabled = true
        }
    }

    private fun showLastSync() {
        val prefs = getSharedPreferences("sync", Context.MODE_PRIVATE)
        val at = prefs.getLong(KEY_SYNCED_AT, 0)
        status.text = if (at == 0L) {
            getString(R.string.status_waiting)
        } else {
            val time = DateFormat.getTimeFormat(this).format(Date(at))
            getString(R.string.status_synced, time, prefs.getInt("count", 0))
        }
    }
}
