package com.memcoach.offline.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.memcoach.offline.data.local.entity.CardProgressEntity

@Dao
interface CardProgressDao {
    @Query("SELECT * FROM card_progress WHERE kidId = :kidId AND cardId = :cardId")
    suspend fun getProgress(kidId: Long, cardId: Long): CardProgressEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(progress: CardProgressEntity)
}
