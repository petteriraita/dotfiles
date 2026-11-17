/* Local API addition to Fossify Clock. GPL-3.0-or-later, like the host app. */
package org.fossify.clock.api

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationManager
import android.content.ContentProvider
import android.content.ContentValues
import android.content.pm.PackageManager
import android.database.Cursor
import android.net.Uri
import android.os.Binder
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import org.fossify.clock.extensions.cancelAlarmClock
import org.fossify.clock.extensions.dbHelper
import org.fossify.clock.extensions.getAlarmIntent
import org.fossify.clock.extensions.getOpenAlarmTabIntent
import org.fossify.clock.helpers.AlarmController
import org.fossify.clock.helpers.TODAY_BIT
import org.fossify.clock.helpers.TOMORROW_BIT
import org.fossify.clock.models.Alarm
import org.fossify.commons.helpers.SILENT
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar

/** No network listener. Only the host app and the installed Termux UID may call. */
class ScheduleProvider : ContentProvider() {
    override fun onCreate() = true
    override fun call(method: String, arg: String?, extras: Bundle?): Bundle {
        val ctx = requireNotNull(context)
        val uid = Binder.getCallingUid()
        val packages = ctx.packageManager.getPackagesForUid(uid)?.toSet() ?: emptySet()
        if (uid != android.os.Process.myUid() && "com.termux" !in packages) {
            throw SecurityException("Schedule API is restricted to the installed Termux UID")
        }
        val identity = Binder.clearCallingIdentity()
        try {
            synchronized(LOCK) {
                val input = JSONObject(arg ?: "{}")
                val result = when (method) {
                    "check" -> readiness()
                    "list" -> JSONObject().put("alarms", JSONArray(ctx.dbHelper.getAlarms().map { record(it) }))
                    "get" -> record(ctx.dbHelper.getAlarmWithId(input.getInt("id")) ?: error("Alarm not found"))
                    "create" -> create(input)
                    "cancel" -> cancel(input)
                    else -> error("Supported commands: check, list, get, create, cancel")
                }
                return Bundle().apply { putString("json", result.put("ok", true).toString()) }
            }
        } catch (e: Exception) {
            return Bundle().apply { putString("json", JSONObject().put("ok", false).put("error", e.javaClass.simpleName + ": " + e.message).toString()) }
        } finally {
            Binder.restoreCallingIdentity(identity)
        }
    }

    private fun readiness(): JSONObject {
        val ctx = requireNotNull(context)
        val manager = ctx.getSystemService(AlarmManager::class.java)
        return JSONObject().put("package", ctx.packageName)
            .put("exactAlarmsAllowed", Build.VERSION.SDK_INT < 31 || manager.canScheduleExactAlarms())
            .put("notificationsAllowed", ctx.getSystemService(NotificationManager::class.java).areNotificationsEnabled())
            .put("batteryOptimizationExempt", ctx.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(ctx.packageName))
            .put("timezone", java.util.TimeZone.getDefault().id)
            .put("nowMillis", System.currentTimeMillis())
    }

    private fun record(alarm: Alarm): JSONObject {
        val p = requireNotNull(context).getSharedPreferences(PREFS, 0)
        return JSONObject().put("id", alarm.id).put("label", alarm.label)
            .put("enabled", alarm.isEnabled).put("vibrate", alarm.vibrate)
            .put("silent", alarm.soundUri == SILENT).put("soundUri", alarm.soundUri)
            .put("oneShot", alarm.oneShot).put("days", alarm.days)
            .put("timeInMinutes", alarm.timeInMinutes)
            .put("atMillis", p.getLong("at:${alarm.id}", 0))
            .put("receiverFiredAtMillis", p.getLong("fired:${alarm.id}", 0))
            .put("vibrationRequestedAtMillis", p.getLong("vibrated:${alarm.id}", 0))
    }

    private fun create(input: JSONObject): JSONObject {
        val ctx = requireNotNull(context)
        val ready = readiness()
        check(ready.getBoolean("exactAlarmsAllowed")) { "Allow exact alarms for this app before scheduling" }
        check(ready.getBoolean("notificationsAllowed")) { "Allow notifications for this app before scheduling" }
        val label = input.getString("label").trim()
        require(label.isNotEmpty() && label.length <= 200) { "Action label must have 1–200 characters" }
        val at = input.getLong("atMillis")
        require(at > System.currentTimeMillis() + 5000 && at < System.currentTimeMillis() + 366L * 86400000) { "Time must be future, within one year" }
        val targetDay = Calendar.getInstance().apply { timeInMillis = at }
        val todayDay = Calendar.getInstance()
        val tomorrowDay = Calendar.getInstance().apply { add(Calendar.DAY_OF_MONTH, 1) }
        fun sameDay(a: Calendar, b: Calendar) = a.get(Calendar.YEAR) == b.get(Calendar.YEAR) && a.get(Calendar.DAY_OF_YEAR) == b.get(Calendar.DAY_OF_YEAR)
        require(sameDay(targetDay, todayDay) || sameDay(targetDay, tomorrowDay)) { "This API currently supports today or tomorrow only; later dates need separate date support" }
        val key = input.getString("key")
        require(key.matches(Regex("[A-Za-z0-9_-]{8,100}"))) { "Invalid idempotency key" }
        val prefs = ctx.getSharedPreferences(PREFS, 0)
        val existing = prefs.getInt("key:$key", -1)
        if (existing != -1) {
            val old = ctx.dbHelper.getAlarmWithId(existing) ?: error("Previous request was removed; inspect before using another key")
            check(old.label == label && prefs.getLong("at:$existing", 0) == at) { "Idempotency key conflicts with an earlier request" }
            return record(old).put("created", false)
        }
        val target = Calendar.getInstance().apply { timeInMillis = at }
        val today = Calendar.getInstance()
        val days = if (target.get(Calendar.YEAR) == today.get(Calendar.YEAR) && target.get(Calendar.DAY_OF_YEAR) == today.get(Calendar.DAY_OF_YEAR)) TODAY_BIT else TOMORROW_BIT
        val alarm = Alarm(0, target.get(Calendar.HOUR_OF_DAY) * 60 + target.get(Calendar.MINUTE), days, true, true,
            ctx.getString(org.fossify.commons.R.string.no_sound), SILENT, label, true)
        val id = ctx.dbHelper.insertAlarm(alarm)
        check(id > 0) { "Alarm database insert failed" }
        alarm.id = id
        try {
            check(prefs.edit().putLong("at:$id", at).putInt("key:$key", id).commit()) { "Cannot persist absolute alarm time" }
            // Direct native call: errors propagate instead of being swallowed by a UI helper.
            ctx.getSystemService(AlarmManager::class.java).setAlarmClock(
                AlarmManager.AlarmClockInfo(at, ctx.getOpenAlarmTabIntent()), ctx.getAlarmIntent(alarm))
            val stored = ctx.dbHelper.getAlarmWithId(id) ?: error("Saved alarm is missing")
            check(stored.vibrate && stored.soundUri == SILENT && stored.isEnabled) { "Saved alarm settings do not match request" }
            return record(stored).put("created", true).put("nativeRegistrationReturned", true)
        } catch (e: Exception) {
            ctx.cancelAlarmClock(alarm)
            ctx.dbHelper.deleteAlarms(arrayListOf(alarm))
            prefs.edit().remove("at:$id").remove("key:$key").commit()
            throw e
        }
    }

    private fun cancel(input: JSONObject): JSONObject {
        val ctx = requireNotNull(context)
        val id = input.getInt("id")
        val prefs = ctx.getSharedPreferences(PREFS, 0)
        check(prefs.contains("at:$id")) { "Only API-created alarms may be cancelled through this interface" }
        val alarm = ctx.dbHelper.getAlarmWithId(id) ?: return JSONObject().put("id", id).put("cancelled", true)
        ctx.cancelAlarmClock(alarm)
        AlarmController.getInstance(ctx).silenceAlarm(id)
        check(ctx.dbHelper.updateAlarmEnabledState(id, false)) { "Cannot disable alarm record" }
        return record(ctx.dbHelper.getAlarmWithId(id) ?: error("Alarm record missing")).put("cancelled", true)
    }

    override fun query(uri: Uri, projection: Array<out String>?, selection: String?, selectionArgs: Array<out String>?, sortOrder: String?): Cursor? = throw UnsupportedOperationException("Use the call interface")
    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = throw UnsupportedOperationException()
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = throw UnsupportedOperationException()
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?): Int = throw UnsupportedOperationException()

    companion object {
        const val PREFS = "local_schedule_api"
        private val LOCK = Any()
    }
}
