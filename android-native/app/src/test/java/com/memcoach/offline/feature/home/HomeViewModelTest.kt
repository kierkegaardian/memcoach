package com.memcoach.offline.feature.home

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import com.memcoach.offline.domain.model.Card
import com.memcoach.offline.domain.model.Deck
import com.memcoach.offline.domain.model.Kid
import com.memcoach.offline.domain.repository.AppPreferences
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import com.memcoach.offline.domain.repository.CardRepository
import com.memcoach.offline.domain.repository.DeckRepository
import com.memcoach.offline.domain.repository.KidRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TestWatcher
import org.junit.runner.Description

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun startReviewWithoutSelectionShowsSelectionMessage() = runTest {
        val viewModel = HomeViewModel(
            appPreferencesRepository = FakeAppPreferencesRepository(),
            kidRepository = FakeKidRepository(),
            deckRepository = FakeDeckRepository(),
            cardRepository = FakeCardRepository(),
        )

        advanceUntilIdle()
        viewModel.startReview()
        advanceUntilIdle()

        assertFalse(viewModel.state.value.canStartReview)
        assertEquals("Select a kid and deck first.", viewModel.state.value.statusMessage)
    }

    @Test
    fun emptySelectedDeckDisablesReviewAndShowsMessage() = runTest {
        val viewModel = HomeViewModel(
            appPreferencesRepository = FakeAppPreferencesRepository(),
            kidRepository = FakeKidRepository(initialKids = listOf(Kid(id = 1L, name = "Kid"))),
            deckRepository = FakeDeckRepository(initialDecks = listOf(Deck(id = 10L, name = "Deck"))),
            cardRepository = FakeCardRepository(initialCardCounts = mapOf(10L to 0)),
        )

        advanceUntilIdle()

        assertEquals(10L, viewModel.state.value.selectedDeckId)
        assertEquals(0, viewModel.state.value.selectedDeckCardCount)
        assertFalse(viewModel.state.value.canStartReview)

        viewModel.startReview()
        advanceUntilIdle()

        assertEquals(
            "Add at least one card to this deck before starting review.",
            viewModel.state.value.statusMessage,
        )
    }

    @Test
    fun addingFirstCardEnablesReview() = runTest {
        val cardRepository = FakeCardRepository(initialCardCounts = mapOf(10L to 0))
        val viewModel = HomeViewModel(
            appPreferencesRepository = FakeAppPreferencesRepository(),
            kidRepository = FakeKidRepository(initialKids = listOf(Kid(id = 1L, name = "Kid"))),
            deckRepository = FakeDeckRepository(initialDecks = listOf(Deck(id = 10L, name = "Deck"))),
            cardRepository = cardRepository,
        )

        advanceUntilIdle()
        assertFalse(viewModel.state.value.canStartReview)

        cardRepository.setCardCount(deckId = 10L, count = 1)
        advanceUntilIdle()

        assertEquals(1, viewModel.state.value.selectedDeckCardCount)
        assertTrue(viewModel.state.value.canStartReview)
    }

    @Test
    fun nonEmptyDeckNavigatesToReview() = runTest {
        val viewModel = HomeViewModel(
            appPreferencesRepository = FakeAppPreferencesRepository(),
            kidRepository = FakeKidRepository(initialKids = listOf(Kid(id = 1L, name = "Kid"))),
            deckRepository = FakeDeckRepository(initialDecks = listOf(Deck(id = 10L, name = "Deck"))),
            cardRepository = FakeCardRepository(initialCardCounts = mapOf(10L to 1)),
        )

        advanceUntilIdle()
        viewModel.startReview()
        advanceUntilIdle()

        assertEquals(
            HomeEvent.NavigateToReview(kidId = 1L, deckId = 10L),
            viewModel.events.first(),
        )
    }

    @Test
    fun repositoryEmissionDoesNotRevertPendingKidSelection() = runTest {
        val preferences = FakeAppPreferencesRepository(
            initialPreferences = AppPreferences(selectedKidId = 1L),
            persistSelections = false,
        )
        val kids = FakeKidRepository(
            initialKids = listOf(Kid(id = 1L, name = "First"), Kid(id = 2L, name = "Second")),
        )
        val viewModel = HomeViewModel(
            appPreferencesRepository = preferences,
            kidRepository = kids,
            deckRepository = FakeDeckRepository(),
            cardRepository = FakeCardRepository(),
        )
        advanceUntilIdle()
        assertEquals(1L, viewModel.state.value.selectedKidId)

        viewModel.selectKid(2L)
        advanceUntilIdle()
        kids.setKids(
            listOf(
                Kid(id = 1L, name = "First"),
                Kid(id = 2L, name = "Second"),
                Kid(id = 3L, name = "Third"),
            ),
        )
        advanceUntilIdle()

        assertEquals(2L, viewModel.state.value.selectedKidId)
    }
}

private class FakeAppPreferencesRepository(
    initialPreferences: AppPreferences = AppPreferences(),
    private val persistSelections: Boolean = true,
) : AppPreferencesRepository {
    private val preferences = MutableStateFlow(initialPreferences)

    override fun observePreferences(): Flow<AppPreferences> = preferences

    override suspend fun setChildModeEnabled(enabled: Boolean) {
        preferences.update { it.copy(childModeEnabled = enabled) }
    }

    override suspend fun setParentPin(pin: String) {
        preferences.update { it.copy(hasParentPin = pin.isNotBlank()) }
    }

    override suspend fun clearParentPin() {
        preferences.update { it.copy(hasParentPin = false) }
    }

    override suspend fun verifyParentPin(pin: String): Boolean = pin == "1234"

    override suspend fun setSelectedKidId(kidId: Long?) {
        if (persistSelections) {
            preferences.update { it.copy(selectedKidId = kidId) }
        }
    }

    override suspend fun setSelectedDeckId(deckId: Long?) {
        if (persistSelections) {
            preferences.update { it.copy(selectedDeckId = deckId) }
        }
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class MainDispatcherRule(
    private val dispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) {
        Dispatchers.setMain(dispatcher)
    }

    override fun finished(description: Description) {
        Dispatchers.resetMain()
    }
}

private class FakeKidRepository(
    initialKids: List<Kid> = emptyList(),
) : KidRepository {
    private val kids = MutableStateFlow(initialKids)

    override fun observeKids(): Flow<List<Kid>> = kids

    override suspend fun addKid(name: String): Long? {
        val cleanedName = name.trim()
        if (cleanedName.isEmpty()) {
            return null
        }
        val nextId = (kids.value.maxOfOrNull { it.id } ?: 0L) + 1L
        kids.update { current -> current + Kid(id = nextId, name = cleanedName) }
        return nextId
    }

    fun setKids(value: List<Kid>) {
        kids.value = value
    }
}

private class FakeDeckRepository(
    initialDecks: List<Deck> = emptyList(),
) : DeckRepository {
    private val decks = MutableStateFlow(initialDecks)

    override fun observeDecks(): Flow<List<Deck>> = decks

    override suspend fun addDeck(name: String): Long? {
        val cleanedName = name.trim()
        if (cleanedName.isEmpty()) {
            return null
        }
        val nextId = (decks.value.maxOfOrNull { it.id } ?: 0L) + 1L
        decks.update { current -> current + Deck(id = nextId, name = cleanedName) }
        return nextId
    }

    override suspend fun getDeck(deckId: Long): Deck? {
        return decks.value.firstOrNull { it.id == deckId }
    }
}

private class FakeCardRepository(
    initialCardCounts: Map<Long, Int> = emptyMap(),
) : CardRepository {
    private val cardCounts = initialCardCounts.mapValuesTo(mutableMapOf()) { MutableStateFlow(it.value) }

    override fun observeCards(deckId: Long): Flow<List<Card>> = flowOf(emptyList())

    override fun observeCardCount(deckId: Long): Flow<Int> = flowForDeck(deckId)

    override suspend fun addCard(deckId: Long, prompt: String, fullText: String): Long? {
        if (prompt.trim().isEmpty() || fullText.trim().isEmpty()) {
            return null
        }
        val nextCount = flowForDeck(deckId).value + 1
        flowForDeck(deckId).value = nextCount
        return nextCount.toLong()
    }

    fun setCardCount(deckId: Long, count: Int) {
        flowForDeck(deckId).value = count
    }

    private fun flowForDeck(deckId: Long): MutableStateFlow<Int> {
        return cardCounts.getOrPut(deckId) { MutableStateFlow(0) }
    }
}
