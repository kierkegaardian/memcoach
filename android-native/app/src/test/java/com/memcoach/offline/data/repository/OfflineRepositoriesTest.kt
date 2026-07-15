package com.memcoach.offline.data.repository

import android.content.Context
import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.memcoach.offline.data.local.MemCoachDatabase
import com.memcoach.offline.domain.model.RecallGrade
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class OfflineRepositoriesTest {
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    private lateinit var database: MemCoachDatabase
    private lateinit var kidRepository: KidRepositoryImpl
    private lateinit var deckRepository: DeckRepositoryImpl
    private lateinit var cardRepository: CardRepositoryImpl
    private lateinit var reviewRepository: ReviewRepositoryImpl

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, MemCoachDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        kidRepository = KidRepositoryImpl(database.kidDao())
        deckRepository = DeckRepositoryImpl(database.deckDao())
        cardRepository = CardRepositoryImpl(database.cardDao())
        reviewRepository = ReviewRepositoryImpl(
            database = database,
            cardDao = database.cardDao(),
            cardProgressDao = database.cardProgressDao(),
            reviewDao = database.reviewDao(),
        )
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun repositoryCrudCreatesAndReadsData() = runTest {
        val kidId = kidRepository.addKid("Alice")
        val deckId = deckRepository.addDeck("Memory Deck")
        assertNotNull(kidId)
        assertNotNull(deckId)

        val cardId = cardRepository.addCard(
            deckId = deckId!!,
            prompt = "Recite John 3:16",
            fullText = "For God so loved the world",
        )
        assertNotNull(cardId)

        val kids = kidRepository.observeKids().first()
        val decks = deckRepository.observeDecks().first()
        val cards = cardRepository.observeCards(deckId).first()

        assertEquals(1, kids.size)
        assertEquals("Alice", kids.first().name)
        assertEquals(1, decks.size)
        assertEquals("Memory Deck", decks.first().name)
        assertEquals(1, cards.size)
        assertEquals("Recite John 3:16", cards.first().prompt)
    }

    @Test
    fun observeCardCountStartsAtZeroAndIncrementsAfterInsert() = runTest {
        val deckId = deckRepository.addDeck("Count Deck")
        assertNotNull(deckId)

        val emptyCount = cardRepository.observeCardCount(deckId!!).first()
        assertEquals(0, emptyCount)

        val inserted = cardRepository.addCard(
            deckId = deckId,
            prompt = "Prompt",
            fullText = "Full text",
        )
        assertNotNull(inserted)

        val updatedCount = cardRepository.observeCardCount(deckId).first()
        assertEquals(1, updatedCount)
    }

    @Test
    fun submitReviewUpdatesProgressAndLogsReview() = runTest {
        val kidId = kidRepository.addKid("Tester")!!
        val deckId = deckRepository.addDeck("Deck")!!
        val cardId = cardRepository.addCard(
            deckId = deckId,
            prompt = "Prompt",
            fullText = "exact text",
        )!!

        val dueCard = reviewRepository.getNextDueCard(kidId = kidId, deckId = deckId)
        assertNotNull(dueCard)

        val result = reviewRepository.submitReview(
            kidId = kidId,
            cardId = cardId,
            userText = "exact text",
            startedAtEpochMillis = null,
        )

        assertEquals(RecallGrade.PERFECT, result.grade)
        assertEquals(6, result.nextIntervalDays)
        assertEquals(1, database.reviewDao().countAll())

        val progress = database.cardProgressDao().getProgress(kidId = kidId, cardId = cardId)
        assertNotNull(progress)
        assertEquals(result.nextIntervalDays, progress?.intervalDays)
        assertEquals(result.nextStreak, progress?.streak)

        val nextDue = reviewRepository.getNextDueCard(kidId = kidId, deckId = deckId)
        assertNull(nextDue)
    }
}
