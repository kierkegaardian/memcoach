package com.memcoach.offline.data.repository

import com.memcoach.offline.data.local.dao.DeckDao
import com.memcoach.offline.data.local.entity.DeckEntity
import com.memcoach.offline.domain.model.Deck
import com.memcoach.offline.domain.repository.DeckRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class DeckRepositoryImpl(
    private val deckDao: DeckDao,
) : DeckRepository {
    override fun observeDecks(): Flow<List<Deck>> {
        return deckDao.observeDecks().map { entities ->
            entities.map { entity ->
                Deck(id = entity.id, name = entity.name)
            }
        }
    }

    override suspend fun addDeck(name: String): Long? {
        val cleaned = name.trim()
        if (cleaned.isEmpty()) {
            return null
        }
        val inserted = deckDao.insert(
            DeckEntity(
                name = cleaned,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        return inserted.takeIf { it > 0 }
    }

    override suspend fun getDeck(deckId: Long): Deck? {
        return deckDao.getDeck(deckId)?.let { entity ->
            Deck(id = entity.id, name = entity.name)
        }
    }
}
