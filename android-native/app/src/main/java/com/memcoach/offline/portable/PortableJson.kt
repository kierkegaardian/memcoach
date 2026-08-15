package com.memcoach.offline.portable

import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.text.Normalizer
import java.time.Instant
import java.time.LocalDate
import java.util.UUID
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

object PortableJson {
    const val MAX_BYTES = 20 * 1024 * 1024
    private val timestampPattern = Regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$")
    private val uuidPattern = Regex("^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    private val easePattern = Regex("^\\d+\\.\\d{6}$")
    private val limits = mapOf("kids" to 10_000, "decks" to 10_000, "cards" to 100_000, "progress" to 200_000, "reviews" to 500_000)

    fun parse(bytes: ByteArray, maxBytes: Int = MAX_BYTES): PortablePackage {
        requirePackage(bytes.size <= maxBytes) { "package exceeds byte limit" }
        val text = StandardCharsets.UTF_8.newDecoder().runCatching { decode(bytes.asByteBuffer()).toString() }
            .getOrElse { throw PortablePackageException("package is not valid UTF-8", it) }
        val document = try {
            JSONObject(text)
        } catch (error: JSONException) {
            throw PortablePackageException("package is not valid JSON", error)
        }
        checkDepth(document)
        if (document.has("extensions")) throw PortablePackageException("unsupported section: extensions")
        exact(document, setOf("format", "version", "exported_at", "source", "scope", "counts", "library", "integrity"), "package")
        requirePackage(document.getString("format") == "memcoach.portable" && document.getInt("version") == 1 && document.getString("scope") == "library") {
            "unsupported portable format, scope, or version"
        }
        validateDigest(document)
        return parsePayload(document)
    }

    fun canonicalPayloadBytes(document: JSONObject): ByteArray {
        val payload = JSONObject(document.toString()).apply { remove("integrity") }
        return canonical(payload).toByteArray(StandardCharsets.UTF_8)
    }

    fun canonical(value: Any?): String = when (value) {
        null, JSONObject.NULL -> "null"
        is JSONObject -> value.keys().asSequence().toList().sorted().joinToString(",", "{", "}") { key ->
            "${JSONObject.quote(normalize(key))}:${canonical(value.get(key))}"
        }
        is JSONArray -> (0 until value.length()).joinToString(",", "[", "]") { canonical(value.get(it)) }
        is String -> JSONObject.quote(normalize(value))
        is Boolean -> value.toString()
        is Number -> JSONObject.numberToString(value)
        else -> throw PortablePackageException("unsupported JSON value")
    }

    private fun validateDigest(document: JSONObject) {
        val integrity = document.getJSONObject("integrity")
        exact(integrity, setOf("alg", "sha256"), "integrity")
        val expected = integrity.getString("sha256")
        requirePackage(integrity.getString("alg") == "sha256" && expected.matches(Regex("^[0-9a-f]{64}$"))) {
            "invalid integrity metadata"
        }
        val actual = MessageDigest.getInstance("SHA-256").digest(canonicalPayloadBytes(document))
            .joinToString("") { "%02x".format(it) }
        requirePackage(actual == expected) { "digest mismatch" }
    }

    private fun parsePayload(document: JSONObject): PortablePackage {
        val sourceObject = document.getJSONObject("source")
        exact(sourceObject, setOf("app", "app_version", "installation_id", "platform"), "source")
        val platform = sourceObject.getString("platform")
        requirePackage(platform == "web" || platform == "android") { "invalid source platform" }
        val source = PortableSource(
            bounded(sourceObject, "app", 64), bounded(sourceObject, "app_version", 64),
            uuid(sourceObject, "installation_id"), platform,
        )
        val libraryObject = document.getJSONObject("library")
        exact(libraryObject, limits.keys, "library")
        val library = PortableLibrary(
            items(libraryObject, "kids", ::kid), items(libraryObject, "decks", ::deck),
            items(libraryObject, "cards", ::card), items(libraryObject, "progress", ::progress),
            items(libraryObject, "reviews", ::review),
        )
        val counts = document.getJSONObject("counts")
        exact(counts, limits.keys, "counts")
        library.counts().forEach { (name, count) -> requirePackage(counts.getInt(name) == count) { "count mismatch for $name" } }
        validateGraph(library)
        return PortablePackage(timestamp(document, "exported_at"), source, library)
    }

    private fun kid(value: JSONObject): PortableKid {
        exact(value, setOf("portable_id", "name", "updated_at"), "kid")
        return PortableKid(uuid(value, "portable_id"), bounded(value, "name", 200), timestamp(value, "updated_at"))
    }

    private fun deck(value: JSONObject): PortableDeck {
        exact(value, setOf("portable_id", "name", "updated_at"), "deck")
        return PortableDeck(uuid(value, "portable_id"), bounded(value, "name", 200), timestamp(value, "updated_at"))
    }

    private fun card(value: JSONObject): PortableCard {
        exact(value, setOf("portable_id", "deck_portable_id", "prompt", "full_text", "updated_at"), "card")
        return PortableCard(uuid(value, "portable_id"), uuid(value, "deck_portable_id"), bounded(value, "prompt", 2_000), bounded(value, "full_text", 100_000), timestamp(value, "updated_at"))
    }

    private fun progress(value: JSONObject): PortableProgress {
        exact(value, setOf("portable_id", "kid_portable_id", "card_portable_id", "interval_days", "due_date", "ease_factor", "streak", "last_review"), "progress")
        val ease = bounded(value, "ease_factor", 32)
        requirePackage(ease.matches(easePattern)) { "ease_factor must have six decimal places" }
        val dueDate = value.getString("due_date")
        runCatching { LocalDate.parse(dueDate) }.getOrElse { throw PortablePackageException("invalid due_date", it) }
        return PortableProgress(uuid(value, "portable_id"), uuid(value, "kid_portable_id"), uuid(value, "card_portable_id"), nonnegative(value, "interval_days", 1), dueDate, ease, nonnegative(value, "streak"), nullableTimestamp(value, "last_review"))
    }

    private fun review(value: JSONObject): PortableReview {
        exact(value, setOf("portable_id", "card_portable_id", "kid_portable_id", "grade", "user_text", "duration_seconds", "ts"), "review")
        val grade = value.getString("grade")
        requirePackage(grade in setOf("perfect", "good", "fail")) { "invalid review grade" }
        return PortableReview(uuid(value, "portable_id"), uuid(value, "card_portable_id"), uuid(value, "kid_portable_id"), grade, nullableString(value, "user_text", 100_000), nullableInt(value, "duration_seconds"), timestamp(value, "ts"))
    }

    private fun validateGraph(library: PortableLibrary) {
        val kids = library.kids.map { it.portableId }.toSet()
        val decks = library.decks.map { it.portableId }.toSet()
        val cards = library.cards.map { it.portableId }.toSet()
        requirePackage(library.cards.all { it.deckPortableId in decks }) { "dangling card reference" }
        requirePackage(library.progress.all { it.kidPortableId in kids && it.cardPortableId in cards }) { "dangling progress reference" }
        requirePackage(library.reviews.all { it.kidPortableId in kids && it.cardPortableId in cards }) { "dangling review reference" }
        requirePackage(library.progress.map { it.kidPortableId to it.cardPortableId }.distinct().size == library.progress.size) { "duplicate progress pair" }
    }

    private fun checkDepth(value: Any?, depth: Int = 0) {
        requirePackage(depth <= 12) { "package nesting exceeds limit" }
        when (value) {
            is JSONObject -> value.keys().forEach { checkDepth(value.get(it), depth + 1) }
            is JSONArray -> (0 until value.length()).forEach { checkDepth(value.get(it), depth + 1) }
        }
    }

    private fun <T : PortableIdentified> items(parent: JSONObject, name: String, parser: (JSONObject) -> T): List<T> {
        val array = parent.getJSONArray(name)
        requirePackage(array.length() <= checkNotNull(limits[name])) { "$name exceeds count limit" }
        val parsed = (0 until array.length()).map { parser(array.getJSONObject(it)) }
        val ids = parsed.map { it.portableId }
        requirePackage(ids == ids.sorted() && ids.distinct().size == ids.size) { "$name must have sorted unique portable IDs" }
        return parsed
    }

    private fun exact(value: JSONObject, expected: Set<String>, where: String) =
        requirePackage(value.keys().asSequence().toSet() == expected) { "$where fields invalid" }

    private fun bounded(value: JSONObject, key: String, max: Int): String = normalize(value.getString(key)).also {
        requirePackage(it.isNotEmpty() && it.length <= max) { "$key is invalid" }
    }

    private fun uuid(value: JSONObject, key: String): String = bounded(value, key, 36).also {
        requirePackage(it.matches(uuidPattern) && UUID.fromString(it).toString() == it) { "$key is not a canonical UUID" }
    }

    private fun timestamp(value: JSONObject, key: String): String = value.getString(key).also {
        requirePackage(it.matches(timestampPattern)) { "$key is not a UTC timestamp" }
        runCatching { Instant.parse(it) }.getOrElse { error -> throw PortablePackageException("$key is invalid", error) }
    }

    private fun nullableTimestamp(value: JSONObject, key: String): String? = if (value.isNull(key)) null else timestamp(value, key)
    private fun nullableString(value: JSONObject, key: String, max: Int): String? = if (value.isNull(key)) null else bounded(value, key, max)
    private fun nullableInt(value: JSONObject, key: String): Int? = if (value.isNull(key)) null else nonnegative(value, key)
    private fun nonnegative(value: JSONObject, key: String, minimum: Int = 0): Int = value.getInt(key).also { requirePackage(it >= minimum) { "$key is invalid" } }
    private fun normalize(value: String): String = Normalizer.normalize(value, Normalizer.Form.NFC)
    private inline fun requirePackage(condition: Boolean, message: () -> String) { if (!condition) throw PortablePackageException(message()) }
    private fun ByteArray.asByteBuffer() = java.nio.ByteBuffer.wrap(this)
}
