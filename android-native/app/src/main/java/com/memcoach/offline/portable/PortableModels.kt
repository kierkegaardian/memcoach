package com.memcoach.offline.portable

data class PortableSource(
    val app: String,
    val appVersion: String,
    val installationId: String,
    val platform: String,
)

interface PortableIdentified { val portableId: String }

data class PortableKid(override val portableId: String, val name: String, val updatedAt: String) : PortableIdentified

data class PortableDeck(override val portableId: String, val name: String, val updatedAt: String) : PortableIdentified

data class PortableCard(
    override val portableId: String,
    val deckPortableId: String,
    val prompt: String,
    val fullText: String,
    val updatedAt: String,
) : PortableIdentified

data class PortableProgress(
    override val portableId: String,
    val kidPortableId: String,
    val cardPortableId: String,
    val intervalDays: Int,
    val dueDate: String,
    val easeFactor: String,
    val streak: Int,
    val lastReview: String?,
) : PortableIdentified

data class PortableReview(
    override val portableId: String,
    val cardPortableId: String,
    val kidPortableId: String,
    val grade: String,
    val userText: String?,
    val durationSeconds: Int?,
    val timestamp: String,
) : PortableIdentified

data class PortableLibrary(
    val kids: List<PortableKid>,
    val decks: List<PortableDeck>,
    val cards: List<PortableCard>,
    val progress: List<PortableProgress>,
    val reviews: List<PortableReview>,
) {
    fun counts(): Map<String, Int> = mapOf(
        "kids" to kids.size,
        "decks" to decks.size,
        "cards" to cards.size,
        "progress" to progress.size,
        "reviews" to reviews.size,
    )
}

data class PortablePackage(
    val exportedAt: String,
    val source: PortableSource,
    val library: PortableLibrary,
)

data class ChangeCounts(
    val creates: Int = 0,
    val updates: Int = 0,
    val skips: Int = 0,
    val collisions: Int = 0,
)

enum class ImportMode { MERGE, COPY }

data class ImportPreview(
    val mode: ImportMode,
    val kids: ChangeCounts,
    val decks: ChangeCounts,
    val cards: ChangeCounts,
    val progress: ChangeCounts,
    val reviews: ChangeCounts,
    val warnings: List<String> = emptyList(),
) {
    val canApply: Boolean
        get() = listOf(kids, decks, cards, progress, reviews).none { it.collisions > 0 }
}

class PortablePackageException(message: String, cause: Throwable? = null) :
    IllegalArgumentException(message, cause)
