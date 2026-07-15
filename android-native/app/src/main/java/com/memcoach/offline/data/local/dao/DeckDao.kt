package com.memcoach.offline.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.memcoach.offline.data.local.entity.DeckEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DeckDao {
    @Query("SELECT * FROM decks ORDER BY name")
    fun observeDecks(): Flow<List<DeckEntity>>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(deck: DeckEntity): Long

    @Query("SELECT * FROM decks WHERE id = :deckId")
    suspend fun getDeck(deckId: Long): DeckEntity?
}
