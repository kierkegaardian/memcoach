package com.memcoach.offline.data.repository

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import java.security.MessageDigest
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class AppPreferencesRepositoryTest {
    private lateinit var context: Context

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit().clear().commit()
    }

    @Test
    fun newParentPinsUseSaltedPbkdf2AndVerify() = runTest {
        val repository = AppPreferencesRepositoryImpl(context)

        repository.setParentPin("1234")

        val stored = storedHash()
        assertTrue(stored.startsWith("pbkdf2_sha256$"))
        assertTrue(repository.verifyParentPin("1234"))
        assertFalse(repository.verifyParentPin("9999"))
    }

    @Test
    fun legacySha256PinMigratesAfterSuccessfulVerification() = runTest {
        val legacyHash = MessageDigest.getInstance("SHA-256")
            .digest("1234".toByteArray(Charsets.UTF_8))
            .joinToString(separator = "") { byte -> "%02x".format(byte) }
        preferences().edit().putString(PIN_HASH_KEY, legacyHash).commit()
        val repository = AppPreferencesRepositoryImpl(context)

        assertTrue(repository.verifyParentPin("1234"))
        assertTrue(storedHash().startsWith("pbkdf2_sha256$"))
    }

    private fun storedHash(): String {
        return preferences().getString(PIN_HASH_KEY, null).orEmpty()
    }

    private fun preferences() = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private companion object {
        const val PREFS_NAME = "memcoach-preferences"
        const val PIN_HASH_KEY = "parent_pin_hash"
    }
}
