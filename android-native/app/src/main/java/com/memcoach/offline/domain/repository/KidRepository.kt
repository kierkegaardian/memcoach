package com.memcoach.offline.domain.repository

import com.memcoach.offline.domain.model.Kid
import kotlinx.coroutines.flow.Flow

interface KidRepository {
    fun observeKids(): Flow<List<Kid>>
    suspend fun addKid(name: String): Long?
}
