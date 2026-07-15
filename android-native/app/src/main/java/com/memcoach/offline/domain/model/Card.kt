package com.memcoach.offline.domain.model

import java.time.LocalDate

data class Card(
    val id: Long,
    val deckId: Long,
    val prompt: String,
    val fullText: String,
    val intervalDays: Int,
    val easeFactor: Double,
    val streak: Int,
    val dueDate: LocalDate,
)
