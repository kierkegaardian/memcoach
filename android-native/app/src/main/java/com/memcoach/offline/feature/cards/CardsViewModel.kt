package com.memcoach.offline.feature.cards

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.memcoach.offline.domain.model.Card
import com.memcoach.offline.domain.repository.CardRepository
import com.memcoach.offline.domain.repository.DeckRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CardsUiState(
    val deckId: Long,
    val deckName: String = "Deck",
    val promptInput: String = "",
    val fullTextInput: String = "",
    val cards: List<Card> = emptyList(),
    val statusMessage: String? = null,
)

sealed interface CardsEvent {
    data class Toast(val message: String) : CardsEvent
}

class CardsViewModel(
    private val deckId: Long,
    private val cardRepository: CardRepository,
    private val deckRepository: DeckRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CardsUiState(deckId = deckId))
    val state = _state.asStateFlow()

    private val eventChannel = Channel<CardsEvent>(capacity = Channel.BUFFERED)
    val events = eventChannel.receiveAsFlow()

    init {
        viewModelScope.launch {
            deckRepository.getDeck(deckId)?.let { deck ->
                _state.update { it.copy(deckName = deck.name) }
            }
        }
        viewModelScope.launch {
            cardRepository.observeCards(deckId).collect { cards ->
                _state.update { it.copy(cards = cards) }
            }
        }
    }

    fun onPromptChanged(value: String) {
        _state.update { it.copy(promptInput = value, statusMessage = null) }
    }

    fun onFullTextChanged(value: String) {
        _state.update { it.copy(fullTextInput = value, statusMessage = null) }
    }

    fun addCard() {
        val current = state.value
        viewModelScope.launch {
            val inserted = try {
                cardRepository.addCard(
                    deckId = deckId,
                    prompt = current.promptInput,
                    fullText = current.fullTextInput,
                )
            } catch (_: Exception) {
                _state.update {
                    it.copy(statusMessage = "Unable to add card right now.")
                }
                eventChannel.send(CardsEvent.Toast("Card not added"))
                return@launch
            }

            if (inserted != null) {
                _state.update {
                    it.copy(
                        promptInput = "",
                        fullTextInput = "",
                        statusMessage = "Card added.",
                    )
                }
                eventChannel.send(CardsEvent.Toast("Card added"))
            } else {
                _state.update {
                    it.copy(statusMessage = "Prompt and full text are required.")
                }
                eventChannel.send(CardsEvent.Toast("Card not added"))
            }
        }
    }

    companion object {
        fun factory(
            deckId: Long,
            cardRepository: CardRepository,
            deckRepository: DeckRepository,
        ): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return CardsViewModel(
                        deckId = deckId,
                        cardRepository = cardRepository,
                        deckRepository = deckRepository,
                    ) as T
                }
            }
        }
    }
}
