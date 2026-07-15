package com.memcoach.offline.domain.model

import java.time.LocalDate

enum class RecallGrade {
    PERFECT,
    GOOD,
    FAIL,
}

data class DueReviewCard(
    val cardId: Long,
    val deckId: Long,
    val prompt: String,
    val fullText: String,
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDate: LocalDate,
)

data class ReviewResult(
    val grade: RecallGrade,
    val nextIntervalDays: Int,
    val nextEaseFactor: Double,
    val nextStreak: Int,
    val nextDueDate: LocalDate,
)
