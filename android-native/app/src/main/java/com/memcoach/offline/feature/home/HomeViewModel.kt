package com.memcoach.offline.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.memcoach.offline.domain.model.Deck
import com.memcoach.offline.domain.model.Kid
import com.memcoach.offline.domain.repository.AppPreferences
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import com.memcoach.offline.domain.repository.CardRepository
import com.memcoach.offline.domain.repository.DeckRepository
import com.memcoach.offline.domain.repository.KidRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

private data class HomeRepositoryState(
    val kids: List<Kid>,
    val decks: List<Deck>,
    val preferences: AppPreferences,
    val selectedKidId: Long?,
    val selectedDeckId: Long?,
)

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModel(
    private val appPreferencesRepository: AppPreferencesRepository,
    private val kidRepository: KidRepository,
    private val deckRepository: DeckRepository,
    private val cardRepository: CardRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HomeUiState())
    val state = _state.asStateFlow()

    private val eventChannel = Channel<HomeEvent>(capacity = Channel.BUFFERED)
    val events = eventChannel.receiveAsFlow()

    init {
        viewModelScope.launch {
            combine(
                kidRepository.observeKids(),
                deckRepository.observeDecks(),
                appPreferencesRepository.observePreferences(),
            ) { kids, decks, preferences ->
                Triple(kids, decks, preferences)
            }.flatMapLatest { (kids, decks, preferences) ->
                val current = state.value
                val selectedKidId = preferredKidId(current, kids, preferences)
                val selectedDeckId = preferredDeckId(current, decks, preferences)
                val repositoryState = HomeRepositoryState(
                    kids = kids,
                    decks = decks,
                    preferences = preferences,
                    selectedKidId = selectedKidId,
                    selectedDeckId = selectedDeckId,
                )
                val cardCountFlow: Flow<Int> =
                    if (selectedDeckId == null) flowOf(0) else cardRepository.observeCardCount(selectedDeckId)
                cardCountFlow.map { cardCount -> repositoryState to cardCount }
            }.collect { (repositoryState, selectedDeckCardCount) ->
                _state.update { current ->
                    current.copy(
                        kids = repositoryState.kids,
                        decks = repositoryState.decks,
                        childModeEnabled = repositoryState.preferences.childModeEnabled,
                        hasParentPin = repositoryState.preferences.hasParentPin,
                        isParentUnlocked = resolveUnlocked(current, repositoryState.preferences),
                        selectedKidId = repositoryState.selectedKidId,
                        selectedDeckId = repositoryState.selectedDeckId,
                        selectedDeckCardCount = selectedDeckCardCount,
                        canStartReview = canStartReview(
                            repositoryState.selectedKidId,
                            repositoryState.selectedDeckId,
                            selectedDeckCardCount,
                        ),
                    )
                }
            }
        }
    }

    fun onKidNameChanged(value: String) {
        _state.update { it.copy(kidNameInput = value, statusMessage = null) }
    }

    fun onDeckNameChanged(value: String) {
        _state.update { it.copy(deckNameInput = value, statusMessage = null) }
    }

    fun onParentPinChanged(value: String) {
        _state.update { it.copy(parentPinInput = value.take(12), statusMessage = null) }
    }

    fun selectKid(kidId: Long) {
        if (state.value.childModeEnabled && !state.value.isParentUnlocked) {
            return
        }
        _state.update {
            it.copy(
                selectedKidId = kidId,
                canStartReview = canStartReview(kidId, it.selectedDeckId, it.selectedDeckCardCount),
                statusMessage = null,
            )
        }
        viewModelScope.launch {
            appPreferencesRepository.setSelectedKidId(kidId)
        }
    }

    fun selectDeck(deckId: Long) {
        if (state.value.childModeEnabled && !state.value.isParentUnlocked) {
            return
        }
        _state.update {
            val selectedDeckCardCount = if (deckId == it.selectedDeckId) it.selectedDeckCardCount else 0
            it.copy(
                selectedDeckId = deckId,
                selectedDeckCardCount = selectedDeckCardCount,
                canStartReview = canStartReview(it.selectedKidId, deckId, selectedDeckCardCount),
                statusMessage = null,
            )
        }
        viewModelScope.launch {
            appPreferencesRepository.setSelectedDeckId(deckId)
        }
    }

    fun addKid() {
        val input = state.value.kidNameInput
        viewModelScope.launch {
            val inserted = kidRepository.addKid(input)
            _state.update {
                it.copy(
                    kidNameInput = if (inserted != null) "" else it.kidNameInput,
                    statusMessage = when {
                        inserted != null -> "Kid created."
                        input.trim().isEmpty() -> "Enter a kid name."
                        else -> "Kid already exists."
                    },
                )
            }
            if (inserted != null) {
                _state.update {
                    it.copy(
                        selectedKidId = inserted,
                        canStartReview = canStartReview(inserted, it.selectedDeckId, it.selectedDeckCardCount),
                    )
                }
                appPreferencesRepository.setSelectedKidId(inserted)
            }
        }
    }

    fun addDeck() {
        val input = state.value.deckNameInput
        viewModelScope.launch {
            val inserted = deckRepository.addDeck(input)
            _state.update {
                it.copy(
                    deckNameInput = if (inserted != null) "" else it.deckNameInput,
                    statusMessage = when {
                        inserted != null -> "Deck created."
                        input.trim().isEmpty() -> "Enter a deck name."
                        else -> "Deck already exists."
                    },
                )
            }
            if (inserted != null) {
                _state.update {
                    it.copy(
                        selectedDeckId = inserted,
                        selectedDeckCardCount = 0,
                        canStartReview = canStartReview(it.selectedKidId, inserted, 0),
                    )
                }
                appPreferencesRepository.setSelectedDeckId(inserted)
            }
        }
    }

    fun openSettings() {
        viewModelScope.launch {
            if (state.value.childModeEnabled && !state.value.isParentUnlocked) {
                _state.update { it.copy(statusMessage = "Unlock parent mode to open settings.") }
                return@launch
            }
            eventChannel.send(HomeEvent.NavigateToSettings)
        }
    }

    fun openCards() {
        viewModelScope.launch {
            if (state.value.childModeEnabled && !state.value.isParentUnlocked) {
                _state.update { it.copy(statusMessage = "Unlock parent mode to manage cards.") }
                return@launch
            }
            val deckId = state.value.selectedDeckId
            if (deckId == null) {
                _state.update { it.copy(statusMessage = "Select a deck first.") }
                return@launch
            }
            eventChannel.send(HomeEvent.NavigateToCards(deckId))
        }
    }

    fun unlockParentMode() {
        val pin = state.value.parentPinInput.trim()
        viewModelScope.launch {
            when {
                !state.value.childModeEnabled -> _state.update { it.copy(isParentUnlocked = true, parentPinInput = "") }
                !state.value.hasParentPin -> {
                    _state.update {
                        it.copy(
                            isParentUnlocked = true,
                            parentPinInput = "",
                            statusMessage = "No parent PIN is set yet. Add one in settings before handing over the device.",
                        )
                    }
                }
                appPreferencesRepository.verifyParentPin(pin) -> {
                    _state.update {
                        it.copy(
                            isParentUnlocked = true,
                            parentPinInput = "",
                            statusMessage = "Parent mode unlocked.",
                        )
                    }
                }
                else -> _state.update { it.copy(parentPinInput = "", statusMessage = "Incorrect parent PIN.") }
            }
        }
    }

    fun startReview() {
        viewModelScope.launch {
            val kidId = state.value.selectedKidId
            val deckId = state.value.selectedDeckId
            if (kidId == null || deckId == null) {
                _state.update { it.copy(statusMessage = "Select a kid and deck first.") }
                return@launch
            }
            if (state.value.selectedDeckCardCount == 0) {
                _state.update { it.copy(statusMessage = "Add at least one card to this deck before starting review.") }
                return@launch
            }
            eventChannel.send(HomeEvent.NavigateToReview(kidId, deckId))
        }
    }

    private fun preferredKidId(current: HomeUiState, kids: List<Kid>, preferences: AppPreferences): Long? {
        return current.selectedKidId?.takeIf { id -> kids.any { it.id == id } }
            ?: preferences.selectedKidId?.takeIf { id -> kids.any { it.id == id } }
            ?: kids.firstOrNull()?.id
    }

    private fun preferredDeckId(current: HomeUiState, decks: List<Deck>, preferences: AppPreferences): Long? {
        return current.selectedDeckId?.takeIf { id -> decks.any { it.id == id } }
            ?: preferences.selectedDeckId?.takeIf { id -> decks.any { it.id == id } }
            ?: decks.firstOrNull()?.id
    }

    private fun resolveUnlocked(current: HomeUiState, preferences: AppPreferences): Boolean {
        return when {
            !preferences.childModeEnabled -> true
            !preferences.hasParentPin -> true
            !current.childModeEnabled || !current.hasParentPin -> false
            else -> current.isParentUnlocked
        }
    }

    private fun canStartReview(
        selectedKidId: Long?,
        selectedDeckId: Long?,
        selectedDeckCardCount: Int,
    ): Boolean {
        return selectedKidId != null && selectedDeckId != null && selectedDeckCardCount > 0
    }

}
