package io.github.satoshimiyasaka.rings

import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.core.app.NotificationManagerCompat
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.Wearable

/** Shows whether the minute ring can follow the Clock timer, and opens the setting. */
class SetupActivity : ComponentActivity() {

    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (resources.displayMetrics.widthPixels * 0.12).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(pad, pad, pad, pad)
        }
        status = TextView(this).apply {
            textSize = 15f
            gravity = Gravity.CENTER
        }
        column.addView(status)
        column.addView(Button(this).apply {
            setText(R.string.setup_open)
            setOnClickListener { openSettings() }
        })
        setContentView(ScrollView(this).apply { addView(column) })
        fetchLatestEvents()
    }

    override fun onResume() {
        super.onResume()
        val granted = packageName in NotificationManagerCompat.getEnabledListenerPackages(this)
        status.setText(if (granted) R.string.setup_on else R.string.setup_off)
    }

    private fun openSettings() {
        val detail = Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS).putExtra(
            Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME,
            ComponentName(this, ClockTimerListener::class.java).flattenToString(),
        )
        for (intent in listOf(detail, Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))) {
            try {
                startActivity(intent)
                return
            } catch (_: ActivityNotFoundException) {
            }
        }
        status.setText(R.string.setup_no_settings)
    }

    /** Picks up events the phone sent before this app was installed. */
    private fun fetchLatestEvents() {
        Wearable.getDataClient(this).dataItems.addOnSuccessListener { items ->
            for (item in items) {
                if (item.uri.path == EVENTS_PATH) {
                    val list = DataMapItem.fromDataItem(item).dataMap.getLongArray(KEY_EVENTS)
                    Store.saveEvents(this, list ?: LongArray(0))
                }
            }
            items.release()
        }
    }
}
