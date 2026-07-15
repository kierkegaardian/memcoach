package com.memcoach.offline.domain.repository

import com.memcoach.offline.domain.model.DueReviewCard
import com.memcoach.offline.domain.model.ReviewResult

interface ReviewRepository {
    suspend fun getNextDueCard(kidId: Long, deckId: Long): DueReviewCard?
    suspend fun submitReview(
        kidId: Long,
        cardId: Long,
        userText: String,
        startedAtEpochMillis: Long?,
    ): ReviewResult
}
