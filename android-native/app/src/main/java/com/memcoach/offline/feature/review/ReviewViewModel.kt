package com.memcoach.offline.feature.review

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.memcoach.offline.domain.model.DueReviewCard
import com.memcoach.offline.domain.model.ReviewResult
import com.memcoach.offline.domain.repository.DeckRepository
import com.memcoach.offline.domain.repository.ReviewRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ReviewUiState(
    val kidId: Long,
    val deckId: Long,
    val deckName: String = "Deck",
    val currentCard: DueReviewCard? = null,
    val answerInput: String = "",
    val startedAtEpochMillis: Long? = null,
    val isLoading: Boolean = true,
    val isSubmitting: Boolean = false,
    val lastResult: ReviewResult? = null,
    val statusMessage: String? = null,
)

sealed interface ReviewEvent {
    data object Exit : ReviewEvent
}

class ReviewViewModel(
    private val kidId: Long,
    private val deckId: Long,
    private val reviewRepository: ReviewRepository,
    private val deckRepository: DeckRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(
        ReviewUiState(
            kidId = kidId,
            deckId = deckId,
        ),
    )
    val state = _state.asStateFlow()

    private val eventChannel = Channel<ReviewEvent>(capacity = Channel.BUFFERED)
    val events = eventChannel.receiveAsFlow()

    init {
        viewModelScope.launch {
            deckRepository.getDeck(deckId)?.let { deck ->
                _state.update { it.copy(deckName = deck.name) }
            }
        }
        refresh()
    }

    fun onAnswerChanged(value: String) {
        _state.update { it.copy(answerInput = value, statusMessage = null) }
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, statusMessage = null) }
            val nextCard = reviewRepository.getNextDueCard(kidId = kidId, deckId = deckId)
            _state.update {
                it.copy(
                    currentCard = nextCard,
                    startedAtEpochMillis = if (nextCard != null) System.currentTimeMillis() else null,
                    isLoading = false,
                    statusMessage = if (nextCard == null) "No due cards right now." else null,
                )
            }
        }
    }

    fun submit() {
        if (state.value.isSubmitting) {
            return
        }
        val currentCard = state.value.currentCard ?: return
        val answer = state.value.answerInput.trim()
        if (answer.isEmpty()) {
            _state.update { it.copy(statusMessage = "Type your recall before submitting.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isSubmitting = true, statusMessage = null) }
            val result = try {
                reviewRepository.submitReview(
                    kidId = kidId,
                    cardId = currentCard.cardId,
                    userText = answer,
                    startedAtEpochMillis = state.value.startedAtEpochMillis,
                )
            } catch (_: Exception) {
                _state.update {
                    it.copy(
                        isSubmitting = false,
                        statusMessage = "Unable to save that review right now.",
                    )
                }
                return@launch
            }
            val nextCard = try {
                reviewRepository.getNextDueCard(kidId = kidId, deckId = deckId)
            } catch (_: Exception) {
                _state.update {
                    it.copy(
                        currentCard = null,
                        answerInput = "",
                        startedAtEpochMillis = null,
                        isSubmitting = false,
                        isLoading = false,
                        lastResult = result,
                        statusMessage = "Review saved. Reload to continue.",
                    )
                }
                return@launch
            }
            _state.update {
                it.copy(
                    currentCard = nextCard,
                    answerInput = "",
                    startedAtEpochMillis = if (nextCard != null) System.currentTimeMillis() else null,
                    isSubmitting = false,
                    isLoading = false,
                    lastResult = result,
                    statusMessage = if (nextCard == null) "No due cards right now." else "Review saved.",
                )
            }
        }
    }

    fun goBack() {
        viewModelScope.launch {
            eventChannel.send(ReviewEvent.Exit)
        }
    }

    companion object {
        fun factory(
            kidId: Long,
            deckId: Long,
            reviewRepository: ReviewRepository,
            deckRepository: DeckRepository,
        ): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return ReviewViewModel(
                        kidId = kidId,
                        deckId = deckId,
                        reviewRepository = reviewRepository,
                        deckRepository = deckRepository,
                    ) as T
                }
            }
        }
    }
}
