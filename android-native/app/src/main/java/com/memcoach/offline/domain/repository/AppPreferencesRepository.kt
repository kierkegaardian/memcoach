package com.memcoach.offline.domain.repository

import kotlinx.coroutines.flow.Flow

data class AppPreferences(
    val childModeEnabled: Boolean = false,
    val hasParentPin: Boolean = false,
    val selectedKidId: Long? = null,
    val selectedDeckId: Long? = null,
)

interface AppPreferencesRepository {
    fun observePreferences(): Flow<AppPreferences>

    suspend fun setChildModeEnabled(enabled: Boolean)

    suspend fun setParentPin(pin: String)

    suspend fun clearParentPin()

    suspend fun verifyParentPin(pin: String): Boolean

    suspend fun setSelectedKidId(kidId: Long?)

    suspend fun setSelectedDeckId(deckId: Long?)
}
