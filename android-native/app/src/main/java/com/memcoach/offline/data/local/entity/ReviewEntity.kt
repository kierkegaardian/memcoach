package com.memcoach.offline.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "reviews",
    foreignKeys = [
        ForeignKey(
            entity = CardEntity::class,
            parentColumns = ["id"],
            childColumns = ["cardId"],
            onDelete = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = KidEntity::class,
            parentColumns = ["id"],
            childColumns = ["kidId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["cardId", "kidId"]),
        Index(value = ["kidId"]),
        Index(value = ["createdAtEpochMillis"]),
        Index(value = ["portableId"], unique = true),
    ],
)
data class ReviewEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val cardId: Long,
    val kidId: Long,
    val grade: String,
    val userText: String?,
    val durationSeconds: Int?,
    val createdAtEpochMillis: Long,
    @ColumnInfo(defaultValue = "''")
    val portableId: String,
)
