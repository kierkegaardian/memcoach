package com.memcoach.offline.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

internal object MemCoachRoomMigrations {
    const val CURRENT_VERSION = 2

    val migration1To2 = object : Migration(1, 2) {
        override fun migrate(db: SupportSQLiteDatabase) {
            addPortableIdentity(db, "kids", updatedFrom = "createdAtEpochMillis")
            addPortableIdentity(db, "decks", updatedFrom = "createdAtEpochMillis")
            addPortableIdentity(db, "cards", updatedFrom = "createdAtEpochMillis")
            rebuildProgress(db)
            rebuildReviews(db)
        }
    }

    private fun rebuildProgress(database: SupportSQLiteDatabase) {
        database.execSQL(
            """CREATE TABLE card_progress_v2 (
                kidId INTEGER NOT NULL, cardId INTEGER NOT NULL, intervalDays INTEGER NOT NULL,
                easeFactor REAL NOT NULL, streak INTEGER NOT NULL, dueDateEpochDay INTEGER NOT NULL,
                lastReviewEpochMillis INTEGER, portableId TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(kidId, cardId),
                FOREIGN KEY(kidId) REFERENCES kids(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(cardId) REFERENCES cards(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )""".trimIndent(),
        )
        database.execSQL(
            """INSERT INTO card_progress_v2
                SELECT kidId, cardId, intervalDays, easeFactor, streak, dueDateEpochDay,
                       lastReviewEpochMillis, $UUID_SQL FROM card_progress""".trimIndent(),
        )
        database.execSQL("DROP TABLE card_progress")
        database.execSQL("ALTER TABLE card_progress_v2 RENAME TO card_progress")
        database.execSQL("CREATE INDEX index_card_progress_kidId_dueDateEpochDay ON card_progress (kidId, dueDateEpochDay)")
        database.execSQL("CREATE INDEX index_card_progress_cardId ON card_progress (cardId)")
        database.execSQL("CREATE UNIQUE INDEX index_card_progress_portableId ON card_progress (portableId)")
    }

    private fun rebuildReviews(database: SupportSQLiteDatabase) {
        database.execSQL(
            """CREATE TABLE reviews_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, cardId INTEGER NOT NULL,
                kidId INTEGER NOT NULL, grade TEXT NOT NULL, userText TEXT,
                durationSeconds INTEGER, createdAtEpochMillis INTEGER NOT NULL,
                portableId TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(cardId) REFERENCES cards(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(kidId) REFERENCES kids(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )""".trimIndent(),
        )
        database.execSQL(
            """INSERT INTO reviews_v2
                SELECT id, cardId, kidId, grade, userText, durationSeconds,
                       createdAtEpochMillis, $UUID_SQL FROM reviews""".trimIndent(),
        )
        database.execSQL("DROP TABLE reviews")
        database.execSQL("ALTER TABLE reviews_v2 RENAME TO reviews")
        database.execSQL("CREATE INDEX index_reviews_cardId_kidId ON reviews (cardId, kidId)")
        database.execSQL("CREATE INDEX index_reviews_kidId ON reviews (kidId)")
        database.execSQL("CREATE INDEX index_reviews_createdAtEpochMillis ON reviews (createdAtEpochMillis)")
        database.execSQL("CREATE UNIQUE INDEX index_reviews_portableId ON reviews (portableId)")
    }

    val all: List<Migration> = listOf(migration1To2)

    private fun addPortableIdentity(
        database: SupportSQLiteDatabase,
        table: String,
        updatedFrom: String? = null,
    ) {
        database.execSQL("ALTER TABLE $table ADD COLUMN portableId TEXT NOT NULL DEFAULT ''")
        database.execSQL("UPDATE $table SET portableId = $UUID_SQL")
        database.execSQL(
            "CREATE UNIQUE INDEX index_${table}_portableId ON $table (portableId)",
        )
        if (updatedFrom != null) {
            database.execSQL(
                "ALTER TABLE $table ADD COLUMN updatedAtEpochMillis INTEGER NOT NULL DEFAULT 0",
            )
            database.execSQL("UPDATE $table SET updatedAtEpochMillis = $updatedFrom")
        }
    }

    fun requireCompleteChain(
        migrations: List<Migration> = all,
        currentVersion: Int = CURRENT_VERSION,
    ) {
        val actualSteps = migrations.map { it.startVersion to it.endVersion }
        val requiredSteps = (1 until currentVersion).map { it to it + 1 }
        check(actualSteps == requiredSteps) {
            "Room migrations must contain every monotonic step: $requiredSteps"
        }
    }

    private const val UUID_SQL = """
        lower(hex(randomblob(4))) || '-' ||
        lower(hex(randomblob(2))) || '-' ||
        '4' || substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1 + abs(random() % 4), 1) ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    """
}
