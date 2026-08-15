package com.memcoach.offline.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "cards",
    foreignKeys = [
        ForeignKey(
            entity = DeckEntity::class,
            parentColumns = ["id"],
            childColumns = ["deckId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["deckId"]),
        Index(value = ["dueDateEpochDay"]),
        Index(value = ["portableId"], unique = true),
    ],
)
data class CardEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val deckId: Long,
    val prompt: String,
    val fullText: String,
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDateEpochDay: Long,
    val createdAtEpochMillis: Long,
    @ColumnInfo(defaultValue = "''")
    val portableId: String,
    @ColumnInfo(defaultValue = "0")
    val updatedAtEpochMillis: Long,
)
