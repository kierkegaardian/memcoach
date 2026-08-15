package com.memcoach.offline.grading

import java.util.Locale
import kotlin.math.min

data class GradingThresholds(
    val perfectThreshold: Double = 0.98,
    val goodThreshold: Double = 0.85,
)

object RecallGrader {
    fun gradeRecall(
        fullText: String,
        userText: String,
        thresholds: GradingThresholds = GradingThresholds(),
    ): String {
        if (userText.isBlank()) {
            return "fail"
        }

        val userClean = userText.trim().lowercase(Locale.ROOT)
        val fullClean = fullText.trim().lowercase(Locale.ROOT)
        val ratio = levenshteinRatio(userClean, fullClean)

        return when {
            ratio >= thresholds.perfectThreshold -> "perfect"
            ratio >= thresholds.goodThreshold -> "good"
            else -> "fail"
        }
    }

    fun levenshteinRatio(left: String, right: String): Double {
        if (left.isEmpty() && right.isEmpty()) {
            return 1.0
        }

        val leftCodePoints = left.codePoints().toArray()
        val rightCodePoints = right.codePoints().toArray()
        val distance = indelDistance(leftCodePoints, rightCodePoints)
        val totalLength = leftCodePoints.size + rightCodePoints.size
        if (totalLength == 0) {
            return 1.0
        }

        return (totalLength - distance).toDouble() / totalLength.toDouble()
    }

    private fun indelDistance(left: IntArray, right: IntArray): Int {
        if (left.isEmpty()) {
            return right.size
        }
        if (right.isEmpty()) {
            return left.size
        }

        val previous = IntArray(right.size + 1) { it }
        val current = IntArray(right.size + 1)

        for (i in left.indices) {
            current[0] = i + 1
            for (j in right.indices) {
                val cost = if (left[i] == right[j]) 0 else 2
                current[j + 1] = min(
                    min(current[j] + 1, previous[j + 1] + 1),
                    previous[j] + cost,
                )
            }
            for (k in previous.indices) {
                previous[k] = current[k]
            }
        }

        return previous[right.size]
    }
}
