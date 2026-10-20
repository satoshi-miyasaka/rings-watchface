package io.github.satoshimiyasaka.rings

import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService

/** Receives the events and settings the phone app sends. */
class DataLayerListenerService : WearableListenerService() {
    override fun onDataChanged(events: DataEventBuffer) {
        for (event in events) {
            val item = event.dataItem
            if (event.type == DataEvent.TYPE_CHANGED && item.uri.path == EVENTS_PATH) {
                val map = DataMapItem.fromDataItem(item).dataMap
                Store.save(
                    this,
                    Inputs(
                        events = map.getLongArray(KEY_EVENTS) ?: LongArray(0),
                        daysOff = map.getLongArray(KEY_DAYS_OFF) ?: LongArray(0),
                        phoneBattery = map.getInt(KEY_PHONE_BATTERY, -1),
                        syncedAt = map.getLong(KEY_SYNCED_AT, 0),
                        mode = map.getInt(KEY_MODE, MODE_PER_LAP),
                    ),
                )
            }
        }
    }
}
