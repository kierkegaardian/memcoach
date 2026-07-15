package com.memcoach.offline.scheduling

import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Sm2EngineTest {
    @Test
    fun mapGradeToQualityMatchesPythonMapping() {
        assertEquals(0, Sm2Engine.mapGradeToQuality("fail"))
        assertEquals(3, Sm2Engine.mapGradeToQuality("good"))
        assertEquals(4, Sm2Engine.mapGradeToQuality("perfect"))
        assertEquals(0, Sm2Engine.mapGradeToQuality("unknown"))
    }

    @Test
    fun qualityBelowThreeResetsIntervalAndStreak() {
        val result = Sm2Engine.update(
            cardIntervalDays = 10,
            cardEaseFactor = 2.5,
            quality = 0,
            streak = 8,
            baseDate = LocalDate.of(2026, 3, 1),
        )

        assertEquals(1, result.intervalDays)
        assertEquals(0, result.streak)
        assertEquals(LocalDate.of(2026, 3, 2), result.dueDate)
    }

    @Test
    fun firstSuccessfulRecallWithPerfectSetsSixDayInterval() {
        val result = Sm2Engine.update(
            cardIntervalDays = 1,
            cardEaseFactor = 2.5,
            quality = 4,
            streak = 0,
            baseDate = LocalDate.of(2026, 3, 1),
        )

        assertEquals(6, result.intervalDays)
        assertEquals(1, result.streak)
        assertEquals(LocalDate.of(2026, 3, 7), result.dueDate)
    }

    @Test
    fun firstSuccessfulRecallWithGoodKeepsOneDayIntervalForPythonParity() {
        val result = Sm2Engine.update(
            cardIntervalDays = 1,
            cardEaseFactor = 2.5,
            quality = 3,
            streak = 0,
            baseDate = LocalDate.of(2026, 3, 1),
        )

        assertEquals(1, result.intervalDays)
        assertEquals(LocalDate.of(2026, 3, 2), result.dueDate)
    }

    @Test
    fun intervalRoundingUsesPythonHalfEvenBehavior() {
        val result = Sm2Engine.update(
            cardIntervalDays = 5,
            cardEaseFactor = 2.5,
            quality = 4,
            streak = 2,
            baseDate = LocalDate.of(2026, 3, 1),
        )

        // 5 * 2.5 = 12.5, Python round(12.5) => 12 (half-even)
        assertEquals(12, result.intervalDays)
    }

    @Test
    fun easeFactorHasFloor() {
        val result = Sm2Engine.update(
            cardIntervalDays = 1,
            cardEaseFactor = 1.3,
            quality = 0,
            streak = 0,
            baseDate = LocalDate.of(2026, 3, 1),
        )

        assertTrue(result.easeFactor >= 1.3)
    }
}
