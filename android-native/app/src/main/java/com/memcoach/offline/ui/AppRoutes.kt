package com.memcoach.offline.ui

object AppRoutes {
    const val HOME = "home"
    const val SETTINGS = "settings"
    const val CARDS = "cards/{deckId}"
    const val REVIEW = "review/{kidId}/{deckId}"

    fun cards(deckId: Long): String = "cards/$deckId"
    fun review(kidId: Long, deckId: Long): String = "review/$kidId/$deckId"
}
