package com.memcoach.offline.grading

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

        val userClean = userText.trim().lowercase()
        val fullClean = fullText.trim().lowercase()
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

        val distance = levenshteinDistance(left, right)
        val totalLength = left.length + right.length
        if (totalLength == 0) {
            return 1.0
        }

        return (totalLength - distance).toDouble() / totalLength.toDouble()
    }

    private fun levenshteinDistance(left: String, right: String): Int {
        if (left.isEmpty()) {
            return right.length
        }
        if (right.isEmpty()) {
            return left.length
        }

        val previous = IntArray(right.length + 1) { it }
        val current = IntArray(right.length + 1)

        for (i in left.indices) {
            current[0] = i + 1
            for (j in right.indices) {
                val cost = if (left[i] == right[j]) 0 else 1
                current[j + 1] = min(
                    min(current[j] + 1, previous[j + 1] + 1),
                    previous[j] + cost,
                )
            }
            for (k in previous.indices) {
                previous[k] = current[k]
            }
        }

        return previous[right.length]
    }
}
