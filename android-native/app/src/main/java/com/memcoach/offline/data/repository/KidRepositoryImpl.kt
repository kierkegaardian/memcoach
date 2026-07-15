package com.memcoach.offline.data.repository

import com.memcoach.offline.data.local.dao.KidDao
import com.memcoach.offline.data.local.entity.KidEntity
import com.memcoach.offline.domain.model.Kid
import com.memcoach.offline.domain.repository.KidRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class KidRepositoryImpl(
    private val kidDao: KidDao,
) : KidRepository {
    override fun observeKids(): Flow<List<Kid>> {
        return kidDao.observeKids().map { entities ->
            entities.map { entity ->
                Kid(id = entity.id, name = entity.name)
            }
        }
    }

    override suspend fun addKid(name: String): Long? {
        val cleaned = name.trim()
        if (cleaned.isEmpty()) {
            return null
        }
        val inserted = kidDao.insert(
            KidEntity(
                name = cleaned,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        return inserted.takeIf { it > 0 }
    }
}
