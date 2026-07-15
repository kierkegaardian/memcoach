package com.memcoach.offline.data.local.projection

data class DueCardRow(
    val id: Long,
    val deckId: Long,
    val prompt: String,
    val fullText: String,
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDateEpochDay: Long,
)
