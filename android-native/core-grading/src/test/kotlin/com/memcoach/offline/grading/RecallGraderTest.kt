package com.memcoach.offline.grading

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RecallGraderTest {
    @Test
    fun blankInputFails() {
        assertEquals("fail", RecallGrader.gradeRecall("abc", "  "))
    }

    @Test
    fun exactMatchIsPerfect() {
        assertEquals("perfect", RecallGrader.gradeRecall("John 3:16", "john 3:16"))
    }

    @Test
    fun borderlineInputIsGoodWithoutLlmDependency() {
        val grade = RecallGrader.gradeRecall("the quick brown fox", "the quick brwn fox")
        assertEquals("good", grade)
    }

    @Test
    fun levenshteinRatioIsBounded() {
        val ratio = RecallGrader.levenshteinRatio("kitten", "sitting")
        assertTrue(ratio in 0.0..1.0)
    }
}
