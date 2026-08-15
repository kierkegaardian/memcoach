package com.memcoach.offline.portable

import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import org.json.JSONArray
import org.json.JSONObject

object PortableWriter {
    fun canonicalPayloadBytes(packageValue: PortablePackage): ByteArray =
        PortableJson.canonical(payload(packageValue)).toByteArray(StandardCharsets.UTF_8)

    fun serialize(packageValue: PortablePackage): ByteArray {
        val payload = payload(packageValue)
        val digest = MessageDigest.getInstance("SHA-256").digest(
            PortableJson.canonical(payload).toByteArray(StandardCharsets.UTF_8),
        ).joinToString("") { "%02x".format(it) }
        payload.put("integrity", JSONObject().put("alg", "sha256").put("sha256", digest))
        return PortableJson.canonical(payload).toByteArray(StandardCharsets.UTF_8)
    }

    private fun payload(packageValue: PortablePackage): JSONObject {
        val source = JSONObject()
            .put("app", packageValue.source.app)
            .put("app_version", packageValue.source.appVersion)
            .put("installation_id", packageValue.source.installationId)
            .put("platform", packageValue.source.platform)
        val counts = JSONObject()
        packageValue.library.counts().forEach(counts::put)
        return JSONObject()
            .put("format", "memcoach.portable")
            .put("version", 1)
            .put("exported_at", packageValue.exportedAt)
            .put("source", source)
            .put("scope", "library")
            .put("counts", counts)
            .put("library", library(packageValue.library))
    }

    private fun library(value: PortableLibrary): JSONObject = JSONObject()
        .put("kids", JSONArray(value.kids.sortedBy { it.portableId }.map {
            JSONObject().put("portable_id", it.portableId).put("name", it.name).put("updated_at", it.updatedAt)
        }))
        .put("decks", JSONArray(value.decks.sortedBy { it.portableId }.map {
            JSONObject().put("portable_id", it.portableId).put("name", it.name).put("updated_at", it.updatedAt)
        }))
        .put("cards", JSONArray(value.cards.sortedBy { it.portableId }.map {
            JSONObject().put("portable_id", it.portableId).put("deck_portable_id", it.deckPortableId)
                .put("prompt", it.prompt).put("full_text", it.fullText).put("updated_at", it.updatedAt)
        }))
        .put("progress", JSONArray(value.progress.sortedBy { it.portableId }.map {
            JSONObject().put("portable_id", it.portableId).put("kid_portable_id", it.kidPortableId)
                .put("card_portable_id", it.cardPortableId).put("interval_days", it.intervalDays)
                .put("due_date", it.dueDate).put("ease_factor", it.easeFactor).put("streak", it.streak)
                .put("last_review", it.lastReview ?: JSONObject.NULL)
        }))
        .put("reviews", JSONArray(value.reviews.sortedBy { it.portableId }.map {
            JSONObject().put("portable_id", it.portableId).put("card_portable_id", it.cardPortableId)
                .put("kid_portable_id", it.kidPortableId).put("grade", it.grade)
                .put("user_text", it.userText ?: JSONObject.NULL)
                .put("duration_seconds", it.durationSeconds ?: JSONObject.NULL).put("ts", it.timestamp)
        }))
}
