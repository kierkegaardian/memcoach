package com.memcoach.offline.data.repository

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import com.memcoach.offline.domain.repository.AppPreferences
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

class AppPreferencesRepositoryImpl(context: Context) : AppPreferencesRepository {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val state = MutableStateFlow(readPreferences())

    private val listener =
        SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            state.value = readPreferences()
        }

    init {
        prefs.registerOnSharedPreferenceChangeListener(listener)
    }

    override fun observePreferences(): Flow<AppPreferences> = state.asStateFlow()

    override suspend fun setChildModeEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_CHILD_MODE_ENABLED, enabled).apply()
    }

    override suspend fun setParentPin(pin: String) {
        prefs.edit().putString(KEY_PARENT_PIN_HASH, hashPin(pin)).apply()
    }

    override suspend fun clearParentPin() {
        prefs.edit().remove(KEY_PARENT_PIN_HASH).apply()
    }

    override suspend fun verifyParentPin(pin: String): Boolean {
        val expected = prefs.getString(KEY_PARENT_PIN_HASH, null) ?: return false
        val matches =
            if (expected.startsWith("${PIN_HASH_ALGORITHM}\$")) {
                verifyPbkdf2Pin(pin, expected)
            } else {
                verifyLegacyPin(pin, expected)
            }
        if (matches && !expected.startsWith("${PIN_HASH_ALGORITHM}\$")) {
            prefs.edit().putString(KEY_PARENT_PIN_HASH, hashPin(pin)).apply()
        }
        return matches
    }

    override suspend fun setSelectedKidId(kidId: Long?) {
        prefs.edit().putOptionalLong(KEY_SELECTED_KID_ID, kidId).apply()
    }

    override suspend fun setSelectedDeckId(deckId: Long?) {
        prefs.edit().putOptionalLong(KEY_SELECTED_DECK_ID, deckId).apply()
    }

    private fun readPreferences(): AppPreferences {
        return AppPreferences(
            childModeEnabled = prefs.getBoolean(KEY_CHILD_MODE_ENABLED, false),
            hasParentPin = !prefs.getString(KEY_PARENT_PIN_HASH, null).isNullOrBlank(),
            selectedKidId = prefs.getOptionalLong(KEY_SELECTED_KID_ID),
            selectedDeckId = prefs.getOptionalLong(KEY_SELECTED_DECK_ID),
        )
    }

    private fun hashPin(pin: String): String {
        val salt = ByteArray(PIN_SALT_BYTES).also(SecureRandom()::nextBytes)
        val digest = derivePin(pin, salt, PIN_HASH_ITERATIONS)
        val encodedSalt = Base64.encodeToString(salt, Base64.NO_WRAP)
        val encodedDigest = Base64.encodeToString(digest, Base64.NO_WRAP)
        return "${PIN_HASH_ALGORITHM}\$${PIN_HASH_ITERATIONS}\$${encodedSalt}\$${encodedDigest}"
    }

    private fun verifyPbkdf2Pin(pin: String, storedHash: String): Boolean {
        val parts = storedHash.split("$")
        if (parts.size != 4 || parts[0] != PIN_HASH_ALGORITHM) {
            return false
        }
        val iterations = parts[1].toIntOrNull()?.takeIf { it > 0 } ?: return false
        return try {
            val salt = Base64.decode(parts[2], Base64.NO_WRAP)
            val expected = Base64.decode(parts[3], Base64.NO_WRAP)
            MessageDigest.isEqual(expected, derivePin(pin, salt, iterations))
        } catch (_: IllegalArgumentException) {
            false
        }
    }

    private fun verifyLegacyPin(pin: String, storedHash: String): Boolean {
        val digest = MessageDigest.getInstance("SHA-256")
        val computed = digest.digest(pin.trim().toByteArray(Charsets.UTF_8))
            .joinToString(separator = "") { byte -> "%02x".format(byte) }
        return MessageDigest.isEqual(
            storedHash.toByteArray(Charsets.UTF_8),
            computed.toByteArray(Charsets.UTF_8),
        )
    }

    private fun derivePin(pin: String, salt: ByteArray, iterations: Int): ByteArray {
        val spec = PBEKeySpec(pin.trim().toCharArray(), salt, iterations, PIN_HASH_BITS)
        return try {
            SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }

    private fun SharedPreferences.Editor.putOptionalLong(key: String, value: Long?): SharedPreferences.Editor {
        if (value == null) {
            remove(key)
        } else {
            putLong(key, value)
        }
        return this
    }

    private fun SharedPreferences.getOptionalLong(key: String): Long? {
        return if (contains(key)) getLong(key, 0L) else null
    }

    private companion object {
        const val PREFS_NAME = "memcoach-preferences"
        const val KEY_CHILD_MODE_ENABLED = "child_mode_enabled"
        const val KEY_PARENT_PIN_HASH = "parent_pin_hash"
        const val KEY_SELECTED_KID_ID = "selected_kid_id"
        const val KEY_SELECTED_DECK_ID = "selected_deck_id"
        const val PIN_HASH_ALGORITHM = "pbkdf2_sha256"
        const val PIN_HASH_ITERATIONS = 200_000
        const val PIN_HASH_BITS = 256
        const val PIN_SALT_BYTES = 16
    }
}
