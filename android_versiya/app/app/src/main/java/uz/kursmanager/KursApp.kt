package uz.kursmanager

import android.app.Application
import uz.kursmanager.data.AppDatabase
import uz.kursmanager.data.Repo
import uz.kursmanager.sync.SyncManager
import uz.kursmanager.sync.SyncWorker

class KursApp : Application() {
    lateinit var db: AppDatabase
        private set
    lateinit var sync: SyncManager
        private set
    lateinit var repo: Repo
        private set

    override fun onCreate() {
        super.onCreate()
        db = AppDatabase.get(this)
        sync = SyncManager(this)
        repo = Repo(db, sync)
        // Agar avval ulangan bo'lsa — fon avtomatik sinxronlashishni yoqish
        if (sync.isPaired) {
            SyncWorker.schedulePeriodic(this)
        }
    }
}

fun android.content.Context.app(): KursApp = applicationContext as KursApp
