package com.memcoach.offline.data.repository

import com.memcoach.offline.data.local.dao.CardDao
import com.memcoach.offline.data.local.entity.CardEntity
import com.memcoach.offline.domain.model.Card
import com.memcoach.offline.domain.repository.CardRepository
import java.time.LocalDate
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class CardRepositoryImpl(
    private val cardDao: CardDao,
) : CardRepository {
    override fun observeCards(deckId: Long): Flow<List<Card>> {
        return cardDao.observeCards(deckId).map { entities ->
            entities.map { entity ->
                Card(
                    id = entity.id,
                    deckId = entity.deckId,
                    prompt = entity.prompt,
                    fullText = entity.fullText,
                    intervalDays = entity.intervalDays,
                    easeFactor = entity.easeFactor,
                    streak = entity.streak,
                    dueDate = LocalDate.ofEpochDay(entity.dueDateEpochDay),
                )
            }
        }
    }

    override fun observeCardCount(deckId: Long): Flow<Int> {
        return cardDao.observeCardCount(deckId)
    }

    override suspend fun addCard(deckId: Long, prompt: String, fullText: String): Long? {
        val cleanedPrompt = prompt.trim()
        val cleanedText = fullText.trim()
        if (cleanedPrompt.isEmpty() || cleanedText.isEmpty()) {
            return null
        }
        val inserted = cardDao.insert(
            CardEntity(
                deckId = deckId,
                prompt = cleanedPrompt,
                fullText = cleanedText,
                intervalDays = 1,
                easeFactor = 2.5,
                streak = 0,
                dueDateEpochDay = LocalDate.now().toEpochDay(),
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        return inserted.takeIf { it > 0 }
    }
}
