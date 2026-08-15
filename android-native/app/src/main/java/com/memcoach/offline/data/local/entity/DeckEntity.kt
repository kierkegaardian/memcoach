package com.memcoach.offline.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "decks",
    indices = [Index(value = ["name"], unique = true), Index(value = ["portableId"], unique = true)],
)
data class DeckEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val name: String,
    val createdAtEpochMillis: Long,
    @ColumnInfo(defaultValue = "''")
    val portableId: String,
    @ColumnInfo(defaultValue = "0")
    val updatedAtEpochMillis: Long,
)
