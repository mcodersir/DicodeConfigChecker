package ir.dicode.configchecker

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor

class VpnKickService : VpnService() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action != ACTION_DISCONNECT_ACTIVE_VPN) {
            stopSelf(startId)
            return START_NOT_STICKY
        }

