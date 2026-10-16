package io.github.satoshimiyasaka.rings

import android.content.Context
import android.provider.CalendarContract
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        if (!EventSync.hasPermission(applicationContext)) return Result.success()
        return try {
            EventSync.sync(applicationContext)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        } finally {
            // A content-URI trigger fires once, so arm it again for the next edit.
            if (tags.contains(TAG_ON_CHANGE)) watchCalendar(applicationContext)
        }
    }

    companion object {
        private const val TAG_ON_CHANGE = "on-calendar-change"

        /** Hourly sync plus a sync shortly after any calendar change. */
        fun schedule(context: Context) {
            val wm = WorkManager.getInstance(context)
            wm.enqueueUniquePeriodicWork(
                "hourly-sync",
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS).build(),
            )
            watchCalendar(context)
        }

        fun syncNow(context: Context) {
            WorkManager.getInstance(context).enqueueUniqueWork(
                "sync-now",
                ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<SyncWorker>().build(),
            )
        }

        private fun watchCalendar(context: Context) {
            val constraints = Constraints.Builder()
                .addContentUriTrigger(CalendarContract.CONTENT_URI, true)
                .setTriggerContentUpdateDelay(10, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                "calendar-changed",
                ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<SyncWorker>()
                    .setConstraints(constraints)
                    .addTag(TAG_ON_CHANGE)
                    .build(),
            )
        }
    }
}
