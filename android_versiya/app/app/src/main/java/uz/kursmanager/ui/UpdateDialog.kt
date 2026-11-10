package uz.kursmanager.ui

import android.app.Activity
import android.app.Dialog
import android.text.SpannableString
import android.text.method.LinkMovementMethod
import android.text.style.URLSpan
import android.view.View
import android.view.ViewGroup
import uz.kursmanager.R
import uz.kursmanager.databinding.DialogUpdateBinding
import uz.kursmanager.update.UpdateInfo

private const val RELEASES_URL =
    "https://github.com/hayotbekmaxmudjonov380-arch/kurs-menejeri/releases"

/**
 * Yangilanish oynasi — login-form dizaynidagi qorong'i karta:
 * aylanuvchi yorug'lik, #272727 karta, #3a3a3a versiya panellari,
 * #373737 pill tugmalar.
 *
 * @param forced    majburiy yangilanish — Escape/orqaga tugmasi ishlamaydi
 * @param onUpdate  "Yangilash" bosilganda chaqiriladi
 * @param onExit    majburiy rejimda "Chiqish" bosilganda chaqiriladi
 */
class UpdateDialog(
    activity: Activity,
    private val info: UpdateInfo,
    private val forced: Boolean,
    private val onUpdate: (UpdateDialog) -> Unit,
    private val onExit: (() -> Unit)? = null
) {

    private val b = DialogUpdateBinding.inflate(activity.layoutInflater)

    val dialog = Dialog(activity, R.style.UpdateDialogTheme).apply {
        setContentView(b.root)
        setCancelable(!forced)
        setCanceledOnTouchOutside(!forced)
    }

    init {
        b.tvTitle.text = if (forced) "Yangilanish shart" else "Yangilanish mavjud"
        b.tvSubtitle.text = if (forced) {
            "Ilovaning eski versiyasi ishlamaydi."
        } else {
            "Yangi versiya tayyorlab qo'yildi."
        }
        b.tvCurrent.text = "v${uz.kursmanager.BuildConfig.VERSION_NAME}"
        b.tvNew.text = "v${info.version}"
        b.tvNotes.text = info.notes

        b.tvFooter.visibility = View.GONE

        b.btnUpdate.setOnClickListener { onUpdate(this) }
        b.btnSecondary.text = if (forced) "Chiqish" else "Keyinroq"
        b.btnSecondary.setOnClickListener {
            if (forced) onExit?.invoke() else dialog.dismiss()
        }
    }

    fun show() {
        dialog.show()
        // Karta to'liq kenglikda, atrofida 16dp bo'shliq qoladi
        dialog.window?.setLayout(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
    }

    fun isShowing(): Boolean = dialog.isShowing

    fun dismiss() {
        try {
            dialog.dismiss()
        } catch (_: Exception) {
        }
    }

    fun setStatus(text: String) {
        b.tvStatus.text = text
        b.tvStatus.visibility = if (text.isEmpty()) View.GONE else View.VISIBLE
    }

    fun setBusy(busy: Boolean) {
        b.btnUpdate.isEnabled = !busy
        b.btnSecondary.isEnabled = !busy
        b.btnUpdate.text = if (busy) "Yuklanmoqda..." else "Yangilash"
    }
}
