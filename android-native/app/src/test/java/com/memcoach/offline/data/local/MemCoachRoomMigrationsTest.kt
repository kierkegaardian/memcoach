package com.memcoach.offline.data.local

import org.junit.Assert.assertThrows
import org.junit.Test

class MemCoachRoomMigrationsTest {
    @Test
    fun productionRegistryContainsEveryRequiredStep() {
        MemCoachRoomMigrations.requireCompleteChain()
    }

    @Test
    fun missingStepIsRejectedBeforeRoomOpensDatabase() {
        assertThrows(IllegalStateException::class.java) {
            MemCoachRoomMigrations.requireCompleteChain(
                migrations = emptyList(),
                currentVersion = 2,
            )
        }
    }
}
