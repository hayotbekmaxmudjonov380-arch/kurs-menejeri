package uz.kursmanager.ui

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.SweepGradient
import android.util.AttributeSet
import android.view.animation.LinearInterpolator
import android.widget.FrameLayout

/**
 * Yangilanish oynasining ildiz konteyneri.
 *
 * CSS `conic-gradient` yorug'ligini shu view **o'ziga** chizadi (`onDraw`),
 * bolalar esa uni yopib turadi. Buni alohida child view sifatida qilmaslik
 * sababi: `match_parent` bo'lgan oddiy View `wrap_content` konteynerda
 * `AT_MOST` o'lchashini to'liq egallaydi — oyna ekranning balandligiga
 * cho'zilib ketardi.
 *
 * Yorug'lik kartadan 8dp tashqarida (root padding = 16dp, karta margin = 8dp),
 * radiusi karta radiusidan 8dp katta.
 */
class UpdateDialogRoot @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : FrameLayout(context, attrs, defStyleAttr) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val path = Path()
    private val rect = RectF()
    private val matrix = Matrix()

    private var shader: SweepGradient? = null
    private var angle = 0f
    private var animator: ValueAnimator? = null

    /** Kartaning 24dp radiusi + 8dp qira = 32dp. */
    private val radiusPx = 32f * resources.displayMetrics.density

    init {
        // FrameLayout default'da o'zini chizmaydi — yorug'lik uchun kerak
        setWillNotDraw(false)
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (w <= 0 || h <= 0) return

        // Yorug'lik = padding ichidagi (content) hudud
        rect.set(
            paddingLeft.toFloat(),
            paddingTop.toFloat(),
            (w - paddingRight).toFloat(),
            (h - paddingBottom).toFloat()
        )
        if (rect.isEmpty) return

        // CSS: conic-gradient(transparent 62%, rgba(255,255,255,0.27) 80%,
        //                     #fff 92%, rgba(255,255,255,0.75) 97%, transparent)
        val colors = intArrayOf(
            Color.TRANSPARENT,
            Color.TRANSPARENT,
            Color.argb(70, 255, 255, 255),
            Color.argb(255, 255, 255, 255),
            Color.argb(190, 255, 255, 255),
            Color.TRANSPARENT
        )
        val positions = floatArrayOf(0f, 0.62f, 0.80f, 0.92f, 0.97f, 1f)
        shader = SweepGradient(rect.centerX(), rect.centerY(), colors, positions)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val s = shader ?: return
        if (rect.isEmpty) return

        matrix.reset()
        matrix.postRotate(angle, rect.centerX(), rect.centerY())
        s.setLocalMatrix(matrix)
        paint.shader = s

        path.reset()
        path.addRoundRect(rect, radiusPx, radiusPx, Path.Direction.CW)
        canvas.drawPath(path, paint)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        startSpin()
    }

    override fun onDetachedFromWindow() {
        stopSpin()
        super.onDetachedFromWindow()
    }

    private fun startSpin() {
        if (animator != null) return
        animator = ValueAnimator.ofFloat(0f, 360f).apply {
            duration = 4000L
            repeatCount = ValueAnimator.INFINITE
            repeatMode = ValueAnimator.RESTART
            interpolator = LinearInterpolator()
            addUpdateListener {
                angle = it.animatedValue as Float
                invalidate()
            }
            start()
        }
    }

    private fun stopSpin() {
        animator?.cancel()
        animator = null
    }
}
