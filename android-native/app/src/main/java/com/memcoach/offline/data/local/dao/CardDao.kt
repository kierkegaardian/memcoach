package com.memcoach.offline.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.memcoach.offline.data.local.entity.CardEntity
import com.memcoach.offline.data.local.projection.DueCardRow
import kotlinx.coroutines.flow.Flow

@Dao
interface CardDao {
    @Query("SELECT * FROM cards WHERE deckId = :deckId ORDER BY id")
    fun observeCards(deckId: Long): Flow<List<CardEntity>>

    @Query("SELECT COUNT(*) FROM cards WHERE deckId = :deckId")
    fun observeCardCount(deckId: Long): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(card: CardEntity): Long

    @Query("SELECT * FROM cards WHERE id = :cardId")
    suspend fun getCard(cardId: Long): CardEntity?

    @Query(
        """
        SELECT
            c.id AS id,
            c.deckId AS deckId,
            c.prompt AS prompt,
            c.fullText AS fullText,
            COALESCE(cp.intervalDays, c.intervalDays) AS intervalDays,
            COALESCE(cp.easeFactor, c.easeFactor) AS easeFactor,
            COALESCE(cp.streak, c.streak) AS streak,
            COALESCE(cp.dueDateEpochDay, c.dueDateEpochDay) AS dueDateEpochDay
        FROM cards c
        LEFT JOIN card_progress cp
            ON cp.cardId = c.id AND cp.kidId = :kidId
        WHERE c.deckId = :deckId
            AND COALESCE(cp.dueDateEpochDay, c.dueDateEpochDay) <= :todayEpochDay
        ORDER BY COALESCE(cp.dueDateEpochDay, c.dueDateEpochDay), c.id
        LIMIT 1
        """,
    )
    suspend fun getNextDueCard(kidId: Long, deckId: Long, todayEpochDay: Long): DueCardRow?
}
