package com.memcoach.offline.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.memcoach.offline.data.local.dao.CardDao
import com.memcoach.offline.data.local.dao.CardProgressDao
import com.memcoach.offline.data.local.dao.DeckDao
import com.memcoach.offline.data.local.dao.KidDao
import com.memcoach.offline.data.local.dao.ReviewDao
import com.memcoach.offline.data.local.entity.CardEntity
import com.memcoach.offline.data.local.entity.CardProgressEntity
import com.memcoach.offline.data.local.entity.DeckEntity
import com.memcoach.offline.data.local.entity.KidEntity
import com.memcoach.offline.data.local.entity.ReviewEntity

@Database(
    entities = [
        KidEntity::class,
        DeckEntity::class,
        CardEntity::class,
        CardProgressEntity::class,
        ReviewEntity::class,
    ],
    version = MemCoachRoomMigrations.CURRENT_VERSION,
    exportSchema = true,
)
abstract class MemCoachDatabase : RoomDatabase() {
    abstract fun kidDao(): KidDao
    abstract fun deckDao(): DeckDao
    abstract fun cardDao(): CardDao
    abstract fun cardProgressDao(): CardProgressDao
    abstract fun reviewDao(): ReviewDao
}
