package io.github.satoshimiyasaka.rings

import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService

/** Receives the event list the phone app sends. */
class DataLayerListenerService : WearableListenerService() {
    override fun onDataChanged(events: DataEventBuffer) {
        for (event in events) {
            val item = event.dataItem
            if (event.type == DataEvent.TYPE_CHANGED && item.uri.path == EVENTS_PATH) {
                val list = DataMapItem.fromDataItem(item).dataMap.getLongArray(KEY_EVENTS)
                Store.saveEvents(this, list ?: LongArray(0))
            }
        }
    }
}
