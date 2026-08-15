package com.memcoach.offline.portable

import androidx.room.withTransaction
import androidx.sqlite.db.SupportSQLiteDatabase
import com.memcoach.offline.data.local.MemCoachDatabase
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class PortableImporter(private val database: MemCoachDatabase) {
    private val sql: SupportSQLiteDatabase
        get() = database.openHelper.writableDatabase

    fun preview(packageValue: PortablePackage, mode: ImportMode): ImportPreview {
        if (mode == ImportMode.COPY) return copyPreview(packageValue)
        val warnings = mutableListOf<String>()
        val kids = entityPreview("kids", packageValue.library.kids, true, warnings)
        val decks = entityPreview("decks", packageValue.library.decks, true, warnings)
        val cards = entityPreview("cards", packageValue.library.cards, false, warnings)
        var progressCreates = 0
        var progressUpdates = 0
        var progressSkips = 0
        var progressCollisions = 0
        packageValue.library.progress.forEach { item ->
            if (progressIdConflicts(item)) {
                progressCollisions++
                return@forEach
            }
            val current = nullableLong(
                """SELECT p.lastReviewEpochMillis FROM card_progress p
                   JOIN kids k ON k.id=p.kidId JOIN cards c ON c.id=p.cardId
                   WHERE k.portableId=? AND c.portableId=?""",
                arrayOf(item.kidPortableId, item.cardPortableId),
            )
            val incoming = item.lastReview?.let { Instant.parse(it).toEpochMilli() }
            if (!existsProgress(item)) {
                progressCreates++
            } else if (incoming != null && (current == null || incoming > current)) {
                progressUpdates++
            } else {
                progressSkips++
                if (incoming == current) warnings += "${item.portableId}: equal last_review kept local"
            }
        }
        val reviewCreates = packageValue.library.reviews.count { !exists("reviews", it.portableId) }
        return ImportPreview(
            ImportMode.MERGE, kids, decks, cards,
            ChangeCounts(
                creates = progressCreates,
                updates = progressUpdates,
                skips = progressSkips,
                collisions = progressCollisions,
            ),
            ChangeCounts(creates = reviewCreates, skips = packageValue.library.reviews.size - reviewCreates),
            warnings,
        )
    }

    suspend fun apply(packageValue: PortablePackage, mode: ImportMode): ImportPreview =
        database.withTransaction {
            val result = preview(packageValue, mode)
            require(result.canApply) { "portable import has unique-name collisions" }
            if (mode == ImportMode.COPY) copyContent(packageValue) else merge(packageValue)
            checkForeignKeys()
            result
        }

    private fun copyPreview(packageValue: PortablePackage): ImportPreview {
        val kids = packageValue.library.kids
        val decks = packageValue.library.decks
        val kidCollisions = kids.count { nameExists("kids", it.name) } + kids.size - kids.map { it.name }.distinct().size
        val deckCollisions = decks.count { nameExists("decks", it.name) } + decks.size - decks.map { it.name }.distinct().size
        return ImportPreview(
            ImportMode.COPY,
            ChangeCounts(creates = kids.size, collisions = kidCollisions),
            ChangeCounts(creates = decks.size, collisions = deckCollisions),
            ChangeCounts(creates = packageValue.library.cards.size),
            ChangeCounts(skips = packageValue.library.progress.size),
            ChangeCounts(skips = packageValue.library.reviews.size),
            listOf("copy imports content only; progress and reviews are omitted"),
        )
    }

    private fun entityPreview(
        table: String,
        incoming: List<PortableIdentified>,
        namesUnique: Boolean,
        warnings: MutableList<String>,
    ): ChangeCounts {
        var creates = 0
        var updates = 0
        var skips = 0
        var collisions = 0
        val packageNames = mutableMapOf<String, String>()
        incoming.forEach { item ->
            val name = when (item) {
                is PortableKid -> item.name
                is PortableDeck -> item.name
                else -> null
            }
            if (namesUnique && name != null) {
                val conflicting = idForName(table, name) ?: packageNames[name]
                if (conflicting != null && conflicting != item.portableId) {
                    collisions++
                    return@forEach
                }
                packageNames[name] = item.portableId
            }
            val localUpdated = nullableLong(
                "SELECT updatedAtEpochMillis FROM $table WHERE portableId=?",
                arrayOf(item.portableId),
            )
            val incomingUpdated = when (item) {
                is PortableKid -> Instant.parse(item.updatedAt).toEpochMilli()
                is PortableDeck -> Instant.parse(item.updatedAt).toEpochMilli()
                is PortableCard -> Instant.parse(item.updatedAt).toEpochMilli()
                else -> error("unsupported entity")
            }
            if (!exists(table, item.portableId)) creates++
            else if (localUpdated != null && incomingUpdated > localUpdated) updates++
            else {
                skips++
                if (incomingUpdated == localUpdated) warnings += "${item.portableId}: equal updated_at kept local"
            }
        }
        return ChangeCounts(creates, updates, skips, collisions)
    }

    private fun merge(packageValue: PortablePackage) {
        packageValue.library.kids.forEach { item ->
            mergeNamed("kids", item.portableId, item.name, item.updatedAt)
        }
        packageValue.library.decks.forEach { item ->
            mergeNamed("decks", item.portableId, item.name, item.updatedAt)
        }
        packageValue.library.cards.forEach { item ->
            val updated = Instant.parse(item.updatedAt).toEpochMilli()
            val deckId = idForPortable("decks", item.deckPortableId)
            val current = nullableLong("SELECT updatedAtEpochMillis FROM cards WHERE portableId=?", arrayOf(item.portableId))
            if (!exists("cards", item.portableId)) {
                sql.execSQL(
                    """INSERT INTO cards (deckId,prompt,fullText,intervalDays,easeFactor,streak,
                       dueDateEpochDay,createdAtEpochMillis,portableId,updatedAtEpochMillis)
                       VALUES (?,?,?,1,2.5,0,?,?,?,?)""",
                    arrayOf(deckId, item.prompt, item.fullText, LocalDate.now().toEpochDay(), updated, item.portableId, updated),
                )
            } else if (current != null && updated > current) {
                sql.execSQL(
                    "UPDATE cards SET deckId=?,prompt=?,fullText=?,updatedAtEpochMillis=? WHERE portableId=?",
                    arrayOf(deckId, item.prompt, item.fullText, updated, item.portableId),
                )
            }
        }
        mergeHistory(packageValue)
    }

    private fun mergeNamed(table: String, portableId: String, name: String, updatedAt: String) {
        val updated = Instant.parse(updatedAt).toEpochMilli()
        val current = nullableLong("SELECT updatedAtEpochMillis FROM $table WHERE portableId=?", arrayOf(portableId))
        if (!exists(table, portableId)) {
            sql.execSQL(
                "INSERT INTO $table (name,createdAtEpochMillis,portableId,updatedAtEpochMillis) VALUES (?,?,?,?)",
                arrayOf(name, updated, portableId, updated),
            )
        } else if (current != null && updated > current) {
            sql.execSQL("UPDATE $table SET name=?,updatedAtEpochMillis=? WHERE portableId=?", arrayOf(name, updated, portableId))
        }
    }

    private fun mergeHistory(packageValue: PortablePackage) {
        packageValue.library.progress.forEach { item ->
            val kidId = idForPortable("kids", item.kidPortableId)
            val cardId = idForPortable("cards", item.cardPortableId)
            val incoming = item.lastReview?.let { Instant.parse(it).toEpochMilli() }
            val current = nullableLong("SELECT lastReviewEpochMillis FROM card_progress WHERE kidId=? AND cardId=?", arrayOf(kidId, cardId))
            if (!existsProgress(item)) {
                sql.execSQL(
                    """INSERT INTO card_progress (kidId,cardId,intervalDays,easeFactor,streak,
                       dueDateEpochDay,lastReviewEpochMillis,portableId) VALUES (?,?,?,?,?,?,?,?)""",
                    arrayOf(kidId, cardId, item.intervalDays, item.easeFactor.toDouble(), item.streak, LocalDate.parse(item.dueDate).toEpochDay(), incoming, item.portableId),
                )
            } else if (incoming != null && (current == null || incoming > current)) {
                sql.execSQL(
                    """UPDATE card_progress SET intervalDays=?,easeFactor=?,streak=?,dueDateEpochDay=?,
                       lastReviewEpochMillis=?,portableId=? WHERE kidId=? AND cardId=?""",
                    arrayOf(item.intervalDays, item.easeFactor.toDouble(), item.streak, LocalDate.parse(item.dueDate).toEpochDay(), incoming, item.portableId, kidId, cardId),
                )
            }
        }
        packageValue.library.reviews.forEach { item ->
            sql.execSQL(
                """INSERT OR IGNORE INTO reviews (cardId,kidId,grade,userText,durationSeconds,
                   createdAtEpochMillis,portableId) VALUES (?,?,?,?,?,?,?)""",
                arrayOf(idForPortable("cards", item.cardPortableId), idForPortable("kids", item.kidPortableId), item.grade, item.userText, item.durationSeconds, Instant.parse(item.timestamp).toEpochMilli(), item.portableId),
            )
        }
    }

    private fun copyContent(packageValue: PortablePackage) {
        val now = System.currentTimeMillis()
        val deckIds = mutableMapOf<String, Long>()
        packageValue.library.kids.forEach { item ->
            sql.execSQL("INSERT INTO kids (name,createdAtEpochMillis,portableId,updatedAtEpochMillis) VALUES (?,?,?,?)", arrayOf(item.name, now, UUID.randomUUID().toString(), now))
        }
        packageValue.library.decks.forEach { item ->
            sql.execSQL("INSERT INTO decks (name,createdAtEpochMillis,portableId,updatedAtEpochMillis) VALUES (?,?,?,?)", arrayOf(item.name, now, UUID.randomUUID().toString(), now))
            deckIds[item.portableId] = lastInsertId()
        }
        packageValue.library.cards.forEach { item ->
            sql.execSQL(
                """INSERT INTO cards (deckId,prompt,fullText,intervalDays,easeFactor,streak,
                   dueDateEpochDay,createdAtEpochMillis,portableId,updatedAtEpochMillis)
                   VALUES (?,?,?,1,2.5,0,?,?,?,?)""",
                arrayOf(deckIds.getValue(item.deckPortableId), item.prompt, item.fullText, LocalDate.now().toEpochDay(), now, UUID.randomUUID().toString(), now),
            )
        }
    }

    private fun exists(table: String, portableId: String) = long("SELECT COUNT(*) FROM $table WHERE portableId=?", arrayOf(portableId)) > 0
    private fun existsProgress(item: PortableProgress) = long(
        """SELECT COUNT(*) FROM card_progress p JOIN kids k ON k.id=p.kidId
           JOIN cards c ON c.id=p.cardId WHERE k.portableId=? AND c.portableId=?""",
        arrayOf(item.kidPortableId, item.cardPortableId),
    ) > 0
    private fun progressIdConflicts(item: PortableProgress) = long(
        """SELECT COUNT(*) FROM card_progress p JOIN kids k ON k.id=p.kidId
           JOIN cards c ON c.id=p.cardId WHERE p.portableId=?
           AND (k.portableId != ? OR c.portableId != ?)""",
        arrayOf(item.portableId, item.kidPortableId, item.cardPortableId),
    ) > 0
    private fun nameExists(table: String, name: String) = long("SELECT COUNT(*) FROM $table WHERE name=?", arrayOf(name)) > 0
    private fun idForName(table: String, name: String) = string("SELECT portableId FROM $table WHERE name=?", arrayOf(name))
    private fun idForPortable(table: String, portableId: String) = long("SELECT id FROM $table WHERE portableId=?", arrayOf(portableId))
    private fun lastInsertId() = long("SELECT last_insert_rowid()")
    private fun checkForeignKeys() = check(long("SELECT COUNT(*) FROM pragma_foreign_key_check") == 0L) { "portable import created foreign-key violations" }

    private fun long(query: String, args: Array<out Any?> = emptyArray()): Long = sql.query(query, args).use { cursor -> check(cursor.moveToFirst()); cursor.getLong(0) }
    private fun nullableLong(query: String, args: Array<out Any?>): Long? = sql.query(query, args).use { cursor -> if (!cursor.moveToFirst() || cursor.isNull(0)) null else cursor.getLong(0) }
    private fun string(query: String, args: Array<out Any?>): String? = sql.query(query, args).use { cursor -> if (!cursor.moveToFirst()) null else cursor.getString(0) }
}
