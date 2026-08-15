package com.memcoach.offline.grading

import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

class SharedGradingContractTest {
    @Test
    fun sharedFixtureMatchesKotlin() {
        fixtureRows("fixtures/deterministic-grading-v1.tsv").forEach { row ->
            val expected = row[1]
            val actual = row[2]
            val ratio = RecallGrader.levenshteinRatio(
                expected.trim().lowercase(Locale.ROOT),
                actual.trim().lowercase(Locale.ROOT),
            )
            assertEquals(row[3], "%.6f".format(Locale.ROOT, ratio))
            assertEquals(row[4], RecallGrader.gradeRecall(expected, actual))
        }
    }

    @Test
    fun turkishDefaultLocaleCannotChangeContract() {
        val original = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"))
            assertEquals("perfect", RecallGrader.gradeRecall("I", "i"))
        } finally {
            Locale.setDefault(original)
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
