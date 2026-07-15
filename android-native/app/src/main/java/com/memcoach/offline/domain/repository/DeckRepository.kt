package com.memcoach.offline.domain.repository

import com.memcoach.offline.domain.model.Deck
import kotlinx.coroutines.flow.Flow

interface DeckRepository {
    fun observeDecks(): Flow<List<Deck>>
    suspend fun addDeck(name: String): Long?
    suspend fun getDeck(deckId: Long): Deck?
}
