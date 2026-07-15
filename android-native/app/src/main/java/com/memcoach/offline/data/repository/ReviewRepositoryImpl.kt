package com.memcoach.offline.data.repository

import androidx.room.withTransaction
import com.memcoach.offline.data.local.MemCoachDatabase
import com.memcoach.offline.data.local.dao.CardDao
import com.memcoach.offline.data.local.dao.CardProgressDao
import com.memcoach.offline.data.local.dao.ReviewDao
import com.memcoach.offline.data.local.entity.CardProgressEntity
import com.memcoach.offline.data.local.entity.ReviewEntity
import com.memcoach.offline.domain.model.DueReviewCard
import com.memcoach.offline.domain.model.RecallGrade
import com.memcoach.offline.domain.model.ReviewResult
import com.memcoach.offline.domain.repository.ReviewRepository
import com.memcoach.offline.grading.RecallGrader
import com.memcoach.offline.scheduling.Sm2Engine
import java.time.LocalDate

class ReviewRepositoryImpl(
    private val database: MemCoachDatabase,
    private val cardDao: CardDao,
    private val cardProgressDao: CardProgressDao,
    private val reviewDao: ReviewDao,
) : ReviewRepository {
    override suspend fun getNextDueCard(kidId: Long, deckId: Long): DueReviewCard? {
        val today = LocalDate.now().toEpochDay()
        val row = cardDao.getNextDueCard(kidId = kidId, deckId = deckId, todayEpochDay = today)
            ?: return null
        return DueReviewCard(
            cardId = row.id,
            deckId = row.deckId,
            prompt = row.prompt,
            fullText = row.fullText,
            intervalDays = row.intervalDays,
            easeFactor = row.easeFactor,
            streak = row.streak,
            dueDate = LocalDate.ofEpochDay(row.dueDateEpochDay),
        )
    }

    override suspend fun submitReview(
        kidId: Long,
        cardId: Long,
        userText: String,
        startedAtEpochMillis: Long?,
    ): ReviewResult {
        return database.withTransaction {
            val card = cardDao.getCard(cardId) ?: error("Card $cardId not found")
            val now = System.currentTimeMillis()
            val gradeRaw = RecallGrader.gradeRecall(
                fullText = card.fullText,
                userText = userText,
            )
            val quality = Sm2Engine.mapGradeToQuality(gradeRaw)
            val progress = cardProgressDao.getProgress(kidId = kidId, cardId = cardId)
            val currentInterval = progress?.intervalDays ?: card.intervalDays
            val currentEaseFactor = progress?.easeFactor ?: card.easeFactor
            val currentStreak = progress?.streak ?: card.streak
            val next = Sm2Engine.update(
                cardIntervalDays = currentInterval,
                cardEaseFactor = currentEaseFactor,
                quality = quality,
                streak = currentStreak,
                baseDate = LocalDate.now(),
            )
            val durationSeconds = startedAtEpochMillis?.let { started ->
                ((now - started) / 1000L).toInt().coerceAtLeast(0)
            }

            reviewDao.insert(
                ReviewEntity(
                    cardId = cardId,
                    kidId = kidId,
                    grade = gradeRaw,
                    userText = userText,
                    durationSeconds = durationSeconds,
                    createdAtEpochMillis = now,
                ),
            )

            cardProgressDao.upsert(
                CardProgressEntity(
                    kidId = kidId,
                    cardId = cardId,
                    intervalDays = next.intervalDays,
                    easeFactor = next.easeFactor,
                    streak = next.streak,
                    dueDateEpochDay = next.dueDate.toEpochDay(),
                    lastReviewEpochMillis = now,
                ),
            )

            ReviewResult(
                grade = parseGrade(gradeRaw),
                nextIntervalDays = next.intervalDays,
                nextEaseFactor = next.easeFactor,
                nextStreak = next.streak,
                nextDueDate = next.dueDate,
            )
        }
    }

    private fun parseGrade(raw: String): RecallGrade {
        return when (raw.lowercase()) {
            "perfect" -> RecallGrade.PERFECT
            "good" -> RecallGrade.GOOD
            else -> RecallGrade.FAIL
        }
    }
}
