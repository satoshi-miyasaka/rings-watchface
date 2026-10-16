package io.github.satoshimiyasaka.rings

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.Wearable

/** A small timer whose remaining time shows on the watch face's minute ring. */
class TimerActivity : ComponentActivity() {

    private lateinit var remaining: TextView
    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            render()
            handler.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (resources.displayMetrics.widthPixels * 0.12).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(pad, pad, pad, pad)
        }
        remaining = TextView(this).apply {
            textSize = 22f
            gravity = Gravity.CENTER
        }
        column.addView(remaining)
        for (row in listOf(listOf(1, 3), listOf(5, 10))) {
            val line = LinearLayout(this).apply { gravity = Gravity.CENTER }
            for (m in row) {
                line.addView(Button(this).apply {
                    text = "+${m}分"
                    setOnClickListener { TimerReceiver.add(this@TimerActivity, m); render() }
                })
            }
            column.addView(line)
        }
        column.addView(Button(this).apply {
            setText(R.string.timer_cancel)
            setOnClickListener { TimerReceiver.cancel(this@TimerActivity); render() }
        })
        setContentView(ScrollView(this).apply { addView(column) })
        fetchLatestEvents()
    }

    override fun onResume() {
        super.onResume()
        handler.post(tick)
    }

    override fun onPause() {
        handler.removeCallbacks(tick)
        super.onPause()
    }

    private fun render() {
        val left = (Store.timerEnd(this) - System.currentTimeMillis()) / 1000
        remaining.text = if (left <= 0) {
            getString(R.string.timer_idle)
        } else {
            getString(R.string.timer_left, (left / 60).toInt(), (left % 60).toInt())
        }
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
