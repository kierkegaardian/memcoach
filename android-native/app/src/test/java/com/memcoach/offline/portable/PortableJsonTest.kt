package com.memcoach.offline.portable

import java.nio.charset.StandardCharsets
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class PortableJsonTest {
    @Test
    fun pythonGoldenParsesAndTypedKotlinCanonicalizationMatches() {
        val packageBytes = resource("valid/memcoach-backup-v1.json")
        val packageValue = PortableJson.parse(packageBytes)

        assertEquals(mapOf("kids" to 1, "decks" to 1, "cards" to 1, "progress" to 1, "reviews" to 1), packageValue.library.counts())
        assertArrayEquals(
            resource("canonical/memcoach-backup-v1.payload.json").dropLast(1).toByteArray(),
            PortableWriter.canonicalPayloadBytes(packageValue),
        )
        assertEquals(packageValue, PortableJson.parse(PortableWriter.serialize(packageValue)))
    }

    @Test
    fun parserRejectsBadDigestInvalidUtf8AndOversizeInput() {
        val packageBytes = resource("valid/memcoach-backup-v1.json")
        val badDigest = packageBytes.toString(StandardCharsets.UTF_8)
            .replace(Regex("[0-9a-f]{64}"), "0".repeat(64))
            .toByteArray()
        assertThrows(PortablePackageException::class.java) { PortableJson.parse(badDigest) }
        assertThrows(PortablePackageException::class.java) { PortableJson.parse(byteArrayOf(0xff.toByte())) }
        assertThrows(PortablePackageException::class.java) { PortableJson.parse(packageBytes, maxBytes = 10) }
    }

    @Test
    fun parserRejectsResignedDuplicateIdsAndDanglingReferences() {
        val packageValue = PortableJson.parse(resource("valid/memcoach-backup-v1.json"))
        val duplicate = packageValue.copy(
            library = packageValue.library.copy(
                kids = packageValue.library.kids + packageValue.library.kids.single(),
            ),
        )
        assertThrows(PortablePackageException::class.java) {
            PortableJson.parse(PortableWriter.serialize(duplicate))
        }
        val dangling = packageValue.copy(
            library = packageValue.library.copy(
                cards = packageValue.library.cards.map {
                    it.copy(deckPortableId = "66666666-6666-4666-8666-666666666666")
                },
            ),
        )
        assertThrows(PortablePackageException::class.java) {
            PortableJson.parse(PortableWriter.serialize(dangling))
        }
    }

    private fun resource(name: String): ByteArray =
        checkNotNull(javaClass.classLoader?.getResourceAsStream(name)).use { it.readBytes() }
}
