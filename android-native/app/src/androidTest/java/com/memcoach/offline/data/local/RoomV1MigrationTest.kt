package com.memcoach.offline.data.local

import android.app.Instrumentation
import androidx.room.testing.MigrationTestHelper
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class RoomV1MigrationTest {
    private val instrumentation: Instrumentation =
        InstrumentationRegistry.getInstrumentation()

    @get:Rule
    val helper = MigrationTestHelper(instrumentation, MemCoachDatabase::class.java)

    @Test
    fun populatedProductionV1FixtureOpensWithoutLoss() {
        helper.createDatabase(TEST_DATABASE, 1).use { database ->
            fixtureStatements().forEach(database::execSQL)
            assertProductionCounts(database)
        }

        helper.runMigrationsAndValidate(
            TEST_DATABASE,
            MemCoachRoomMigrations.CURRENT_VERSION,
            true,
            *MemCoachRoomMigrations.all.toTypedArray(),
        ).use { database ->
            assertProductionCounts(database)
            database.query("PRAGMA foreign_key_check").use { cursor ->
                assertFalse(cursor.moveToFirst())
            }
            database.query(
                "SELECT COUNT(*) FROM reviews WHERE userText = '' AND durationSeconds IS NULL",
            ).use { cursor ->
                assertEquals(true, cursor.moveToFirst())
                assertEquals(1, cursor.getInt(0))
            }
            database.query(
                """
                SELECT k.name, d.name, c.prompt, p.lastReviewEpochMillis, r.grade
                FROM card_progress p
                JOIN kids k ON k.id = p.kidId
                JOIN cards c ON c.id = p.cardId
                JOIN decks d ON d.id = c.deckId
                JOIN reviews r ON r.kidId = k.id AND r.cardId = c.id
                """.trimIndent(),
            ).use { cursor ->
                assertEquals(true, cursor.moveToFirst())
                assertEquals("perfect", cursor.getString(4))
            }
            listOf("kids", "decks", "cards", "card_progress", "reviews").forEach { table ->
                database.query("SELECT portableId FROM $table").use { cursor ->
                    val ids = mutableSetOf<String>()
                    while (cursor.moveToNext()) {
                        val value = cursor.getString(0)
                        assertTrue(value.matches(UUID_PATTERN))
                        assertTrue(ids.add(value))
                    }
                }
            }
            listOf("kids", "decks", "cards").forEach { table ->
                database.query("SELECT COUNT(*) FROM $table WHERE updatedAtEpochMillis != createdAtEpochMillis").use { cursor ->
                    assertTrue(cursor.moveToFirst())
                    assertEquals(0, cursor.getInt(0))
                }
            }
        }
    }

    private fun fixtureStatements(): List<String> =
        instrumentation.context.assets
            .open("fixtures/room_v1_populated.sql")
            .bufferedReader()
            .use { it.readText() }
            .split(';')
            .map(String::trim)
            .filter(String::isNotEmpty)

    private fun assertProductionCounts(database: SupportSQLiteDatabase) {
        EXPECTED_COUNTS.forEach { (table, expected) ->
            database.query("SELECT COUNT(*) FROM $table").use { cursor ->
                assertEquals(true, cursor.moveToFirst())
                assertEquals(table, expected, cursor.getInt(0))
            }
        }
    }

    private companion object {
        const val TEST_DATABASE = "room-v1-migration-test"

        val EXPECTED_COUNTS = mapOf(
            "kids" to 2,
            "decks" to 2,
            "cards" to 3,
            "card_progress" to 4,
            "reviews" to 5,
        )
        val UUID_PATTERN = Regex(
            "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )
    }
}
