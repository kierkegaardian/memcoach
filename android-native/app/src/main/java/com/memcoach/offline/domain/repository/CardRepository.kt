package com.memcoach.offline.domain.repository

import com.memcoach.offline.domain.model.Card
import kotlinx.coroutines.flow.Flow

interface CardRepository {
    fun observeCards(deckId: Long): Flow<List<Card>>
    fun observeCardCount(deckId: Long): Flow<Int>
    suspend fun addCard(deckId: Long, prompt: String, fullText: String): Long?
}
