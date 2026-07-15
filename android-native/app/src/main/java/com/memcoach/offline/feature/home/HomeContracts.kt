package com.memcoach.offline.feature.home

import com.memcoach.offline.domain.model.Deck
import com.memcoach.offline.domain.model.Kid

data class HomeUiState(
    val kids: List<Kid> = emptyList(),
    val decks: List<Deck> = emptyList(),
    val childModeEnabled: Boolean = false,
    val hasParentPin: Boolean = false,
    val isParentUnlocked: Boolean = true,
    val selectedKidId: Long? = null,
    val selectedDeckId: Long? = null,
    val selectedDeckCardCount: Int = 0,
    val canStartReview: Boolean = false,
    val kidNameInput: String = "",
    val deckNameInput: String = "",
    val parentPinInput: String = "",
    val statusMessage: String? = null,
)

sealed interface HomeEvent {
    data object NavigateToSettings : HomeEvent
    data class NavigateToCards(val deckId: Long) : HomeEvent
    data class NavigateToReview(val kidId: Long, val deckId: Long) : HomeEvent
}
