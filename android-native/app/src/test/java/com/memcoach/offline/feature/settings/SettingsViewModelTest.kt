package com.memcoach.offline.feature.settings

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import com.memcoach.offline.feature.home.MainDispatcherRule
import com.memcoach.offline.domain.repository.AppPreferences
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SettingsViewModelTest {
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun cannotEnableChildModeWithoutParentPin() = runTest {
        val prefs = FakeSettingsPreferencesRepository()
        val viewModel = SettingsViewModel(appPreferencesRepository = prefs)

        advanceUntilIdle()
        viewModel.setChildMode(true)
        advanceUntilIdle()

        assertFalse(prefs.current.childModeEnabled)
        assertEquals("Set a parent PIN before enabling child mode.", viewModel.state.value.statusMessage)
    }

    @Test
    fun enablingChildModeWithPinSucceeds() = runTest {
        val prefs = FakeSettingsPreferencesRepository(initial = AppPreferences(hasParentPin = true))
        val viewModel = SettingsViewModel(appPreferencesRepository = prefs)

        advanceUntilIdle()
        viewModel.setChildMode(true)
        advanceUntilIdle()

        assertTrue(prefs.current.childModeEnabled)
        assertEquals("Child mode enabled. Parent setup is now PIN-gated.", viewModel.state.value.statusMessage)
    }
}

private class FakeSettingsPreferencesRepository(
    initial: AppPreferences = AppPreferences(),
) : AppPreferencesRepository {
    private val state = MutableStateFlow(initial)

    val current: AppPreferences
        get() = state.value

    override fun observePreferences(): Flow<AppPreferences> = state

    override suspend fun setChildModeEnabled(enabled: Boolean) {
        state.update { it.copy(childModeEnabled = enabled) }
    }

    override suspend fun setParentPin(pin: String) {
        state.update { it.copy(hasParentPin = pin.isNotBlank()) }
    }

    override suspend fun clearParentPin() {
        state.update { it.copy(hasParentPin = false) }
    }

    override suspend fun verifyParentPin(pin: String): Boolean = pin == "1234"

    override suspend fun setSelectedKidId(kidId: Long?) {
        state.update { it.copy(selectedKidId = kidId) }
    }

    override suspend fun setSelectedDeckId(deckId: Long?) {
        state.update { it.copy(selectedDeckId = deckId) }
    }
}
