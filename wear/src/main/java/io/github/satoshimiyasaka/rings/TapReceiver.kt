package io.github.satoshimiyasaka.rings

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/** A tap on the face switches between the coming and the past view. */
class TapReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.i(RingDataSource.TAG, "tap")
        Store.togglePast(context, System.currentTimeMillis())
    }
}
