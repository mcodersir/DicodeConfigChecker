package ir.dicode.configchecker

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor

class VpnKickService : VpnService() {
    private var tunnel: ParcelFileDescriptor? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action != ACTION_DISCONNECT_ACTIVE_VPN) {
            stopSelf(startId)
            return START_NOT_STICKY
        }

        runCatching {
            tunnel?.close()
            tunnel = Builder()
                .setSession("Dicode VPN Disconnect")
                .addAddress("10.254.0.1", 32)
                .addRoute("0.0.0.0", 0)
                .setBlocking(false)
                .establish()
            tunnel?.close()
            tunnel = null
        }

        stopSelf(startId)
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        runCatching { tunnel?.close() }
        tunnel = null
        super.onDestroy()
    }

    companion object {
        const val ACTION_DISCONNECT_ACTIVE_VPN = "ir.dicode.configchecker.DISCONNECT_ACTIVE_VPN"
    }
}
