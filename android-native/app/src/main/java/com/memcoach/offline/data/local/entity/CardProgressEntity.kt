package com.memcoach.offline.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index

@Entity(
    tableName = "card_progress",
    primaryKeys = ["kidId", "cardId"],
    foreignKeys = [
        ForeignKey(
            entity = KidEntity::class,
            parentColumns = ["id"],
            childColumns = ["kidId"],
            onDelete = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = CardEntity::class,
            parentColumns = ["id"],
            childColumns = ["cardId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["kidId", "dueDateEpochDay"]), Index(value = ["cardId"])],
)
data class CardProgressEntity(
    val kidId: Long,
    val cardId: Long,
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDateEpochDay: Long,
    val lastReviewEpochMillis: Long,
)
