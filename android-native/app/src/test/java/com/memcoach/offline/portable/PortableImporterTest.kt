package com.memcoach.offline.portable

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.memcoach.offline.data.local.MemCoachDatabase
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class PortableImporterTest {
    private lateinit var database: MemCoachDatabase
    private lateinit var importer: PortableImporter
    private lateinit var packageValue: PortablePackage

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, MemCoachDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        importer = PortableImporter(database)
        packageValue = PortableJson.parse(resource("valid/memcoach-backup-v1.json"))
    }

    @After
    fun tearDown() = database.close()

    @Test
    fun previewIsReadOnlyMergeIsTransactionalAndIdempotent() = runTest {
        val preview = importer.preview(packageValue, ImportMode.MERGE)
        assertTrue(preview.canApply)
        assertEquals(1, preview.kids.creates)
        assertCounts(0, 0, 0, 0, 0)

        importer.apply(packageValue, ImportMode.MERGE)
        assertCounts(1, 1, 1, 1, 1)

        val second = importer.apply(packageValue, ImportMode.MERGE)
        assertEquals(1, second.kids.skips)
        assertEquals(1, second.progress.skips)
        assertEquals(1, second.reviews.skips)
        assertCounts(1, 1, 1, 1, 1)
    }

    @Test
    fun copyRewritesGraphAndOmitsHistory() = runTest {
        importer.apply(packageValue, ImportMode.COPY)
        assertCounts(1, 1, 1, 0, 0)
        val importedKidId = string("SELECT portableId FROM kids")
        val importedDeckId = string("SELECT portableId FROM decks")
        val importedCardId = string("SELECT portableId FROM cards")
        assertFalse(importedKidId == packageValue.library.kids.single().portableId)
        assertFalse(importedDeckId == packageValue.library.decks.single().portableId)
        assertFalse(importedCardId == packageValue.library.cards.single().portableId)
        assertEquals(1, int("SELECT COUNT(*) FROM cards c JOIN decks d ON d.id=c.deckId"))
    }

    @Test
    fun newerContentAndProgressWinWhileExistingReviewHistoryIsImmutable() = runTest {
        importer.apply(packageValue, ImportMode.MERGE)
        val updated = packageValue.copy(
            library = packageValue.library.copy(
                kids = packageValue.library.kids.map {
                    it.copy(name = "Updated Kid", updatedAt = "2026-07-16T00:00:00Z")
                },
                progress = packageValue.library.progress.map {
                    it.copy(
                        portableId = "99999999-9999-4999-8999-999999999999",
                        intervalDays = 12,
                        lastReview = "2026-07-16T00:00:00Z",
                    )
                },
                reviews = packageValue.library.reviews.map { it.copy(grade = "fail") },
            ),
        )

        val preview = importer.apply(updated, ImportMode.MERGE)

        assertEquals(1, preview.kids.updates)
        assertEquals(1, preview.progress.updates)
        assertEquals(1, preview.reviews.skips)
        assertEquals("Updated Kid", string("SELECT name FROM kids"))
        assertEquals(12, int("SELECT intervalDays FROM card_progress"))
        assertEquals("perfect", string("SELECT grade FROM reviews"))
    }

    @Test
    fun lateReviewFailureRollsBackEarlierEntityAndProgressWrites() = runTest {
        database.openHelper.writableDatabase.execSQL(
            """CREATE TRIGGER fail_portable_review BEFORE INSERT ON reviews
               BEGIN SELECT RAISE(FAIL, 'injected review failure'); END""",
        )
        runCatching { importer.apply(packageValue, ImportMode.MERGE) }
            .onSuccess { error("expected injected failure") }
        assertCounts(0, 0, 0, 0, 0)
    }

    private fun assertCounts(kids: Int, decks: Int, cards: Int, progress: Int, reviews: Int) {
        assertEquals(kids, int("SELECT COUNT(*) FROM kids"))
        assertEquals(decks, int("SELECT COUNT(*) FROM decks"))
        assertEquals(cards, int("SELECT COUNT(*) FROM cards"))
        assertEquals(progress, int("SELECT COUNT(*) FROM card_progress"))
        assertEquals(reviews, int("SELECT COUNT(*) FROM reviews"))
    }

    private fun int(query: String): Int = database.openHelper.writableDatabase.query(query).use {
        check(it.moveToFirst()); it.getInt(0)
    }

    private fun string(query: String): String = database.openHelper.writableDatabase.query(query).use {
        check(it.moveToFirst()); it.getString(0)
    }

    private fun resource(name: String): ByteArray =
        checkNotNull(javaClass.classLoader?.getResourceAsStream(name)).use { it.readBytes() }
}
