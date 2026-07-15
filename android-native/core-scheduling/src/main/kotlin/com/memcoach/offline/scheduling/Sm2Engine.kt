package com.memcoach.offline.scheduling

import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import kotlin.math.max

data class Sm2Result(
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDate: LocalDate,
)

object Sm2Engine {
    fun mapGradeToQuality(grade: String): Int {
        return when (grade.lowercase()) {
            "fail" -> 0
            "good" -> 3
            "perfect" -> 4
            else -> 0
        }
    }

    fun update(
        cardIntervalDays: Int,
        cardEaseFactor: Double,
        quality: Int,
        streak: Int,
        baseDate: LocalDate = LocalDate.now(),
    ): Sm2Result {
        val safeInterval = max(1, cardIntervalDays)
        val safeEaseFactor = max(1.3, cardEaseFactor)

        val nextStreak: Int
        val nextInterval: Int

        if (quality < 3) {
            nextStreak = 0
            nextInterval = 1
        } else {
            nextStreak = streak + 1
            // Keep parity with the current Python app behavior for migration consistency:
            // when interval is 1, only "perfect" advances to a 6-day interval.
            nextInterval = if (safeInterval == 1) {
                if (quality >= 4) 6 else 1
            } else {
                max(1, pythonRound(safeInterval * safeEaseFactor))
            }
        }

        val nextEase = max(
            1.3,
            safeEaseFactor +
                (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )

        return Sm2Result(
            intervalDays = nextInterval,
            easeFactor = nextEase,
            streak = nextStreak,
            dueDate = baseDate.plusDays(nextInterval.toLong()),
        )
    }

    fun getNextInterval(
        quality: Int,
        previousInterval: Int = 1,
        easeFactor: Double = 2.5,
    ): Int {
        return update(
            cardIntervalDays = previousInterval,
            cardEaseFactor = easeFactor,
            quality = quality,
            streak = 0,
        ).intervalDays
    }

    private fun pythonRound(value: Double): Int {
        return BigDecimal.valueOf(value)
            .setScale(0, RoundingMode.HALF_EVEN)
            .toInt()
    }
}
