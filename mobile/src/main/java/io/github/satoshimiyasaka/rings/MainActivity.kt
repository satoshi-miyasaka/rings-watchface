package io.github.satoshimiyasaka.rings

import android.Manifest
import android.content.Context
import android.os.Bundle
import android.text.format.DateFormat
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.util.Date

class MainActivity : ComponentActivity() {

    private lateinit var status: TextView
    private lateinit var action: Button

    private val requestCalendar =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { render() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)
        action = findViewById(R.id.action)
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
            action.isEnabled = false
            lifecycleScope.launch {
                try {
                    EventSync.sync(this@MainActivity)
                } catch (e: Exception) {
                    status.text = e.localizedMessage
                }
                showLastSync()
                action.isEnabled = true
            }
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
