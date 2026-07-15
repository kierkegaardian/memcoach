package com.memcoach.offline.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val childModeEnabled: Boolean = false,
    val hasParentPin: Boolean = false,
    val pinInput: String = "",
    val statusMessage: String? = null,
)

class SettingsViewModel(
    private val appPreferencesRepository: AppPreferencesRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUiState())
    val state = _state.asStateFlow()

    init {
        viewModelScope.launch {
            appPreferencesRepository.observePreferences().collect { preferences ->
                _state.update { current ->
                    current.copy(
                        childModeEnabled = preferences.childModeEnabled,
                        hasParentPin = preferences.hasParentPin,
                    )
                }
            }
        }
    }

    fun onPinChanged(value: String) {
        _state.update { it.copy(pinInput = value.take(12), statusMessage = null) }
    }

    fun setChildMode(enabled: Boolean) {
        viewModelScope.launch {
            if (enabled && !state.value.hasParentPin) {
                _state.update {
                    it.copy(statusMessage = "Set a parent PIN before enabling child mode.")
                }
                return@launch
            }
            appPreferencesRepository.setChildModeEnabled(enabled)
            _state.update {
                it.copy(
                    statusMessage =
                        if (enabled) {
                            "Child mode enabled. Parent setup is now PIN-gated."
                        } else {
                            "Child mode disabled."
                        },
                )
            }
        }
    }

    fun savePin() {
        val pin = state.value.pinInput.trim()
        viewModelScope.launch {
            if (pin.length < 4) {
                _state.update { it.copy(statusMessage = "Use at least 4 digits or characters for the parent PIN.") }
                return@launch
            }
            appPreferencesRepository.setParentPin(pin)
            _state.update {
                it.copy(
                    pinInput = "",
                    hasParentPin = true,
                    statusMessage = "Parent PIN saved.",
                )
            }
        }
    }

    fun clearPin() {
        viewModelScope.launch {
            appPreferencesRepository.clearParentPin()
            _state.update {
                it.copy(
                    pinInput = "",
                    hasParentPin = false,
                    statusMessage = "Parent PIN cleared.",
                )
            }
        }
    }

    companion object {
        fun factory(
            appPreferencesRepository: AppPreferencesRepository,
        ): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return SettingsViewModel(appPreferencesRepository = appPreferencesRepository) as T
                }
            }
        }
    }
}
