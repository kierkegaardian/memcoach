package com.memcoach.offline.scheduling

import java.time.LocalDate
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

class SharedSm2ContractTest {
    @Test
    fun sharedFixtureMatchesKotlin() {
        fixtureRows("fixtures/sm2-v1.tsv").forEach { row ->
            val quality = Sm2Engine.mapGradeToQuality(row[1])
            assertEquals(row[2].toInt(), quality)
            val result = Sm2Engine.update(
                cardIntervalDays = row[3].toInt(),
                cardEaseFactor = row[4].toDouble(),
                quality = quality,
                streak = row[5].toInt(),
                baseDate = LocalDate.parse(row[6]),
            )
            assertEquals(row[7].toInt(), result.intervalDays)
            assertEquals(row[8], "%.6f".format(Locale.ROOT, result.easeFactor))
            assertEquals(row[9].toInt(), result.streak)
            assertEquals(LocalDate.parse(row[10]), result.dueDate)
        }
    }

    private fun fixtureRows(resource: String): List<List<String>> =
        checkNotNull(javaClass.classLoader?.getResourceAsStream(resource))
            .bufferedReader()
            .use { it.readLines() }
            .drop(1)
            .filter(String::isNotEmpty)
            .map { it.split('\t') }
}
