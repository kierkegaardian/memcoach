package com.memcoach.offline.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.memcoach.offline.data.local.entity.ReviewEntity

@Dao
interface ReviewDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(review: ReviewEntity): Long

    @Query("SELECT COUNT(*) FROM reviews")
    suspend fun countAll(): Int
}
