package com.memcoach.offline.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.memcoach.offline.data.local.entity.KidEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface KidDao {
    @Query("SELECT * FROM kids ORDER BY name")
    fun observeKids(): Flow<List<KidEntity>>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(kid: KidEntity): Long
}
