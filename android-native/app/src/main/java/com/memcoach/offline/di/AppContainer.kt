package com.memcoach.offline.di

import android.content.Context
import androidx.room.Room
import com.memcoach.offline.data.local.MemCoachDatabase
import com.memcoach.offline.data.local.MemCoachRoomMigrations
import com.memcoach.offline.data.repository.AppPreferencesRepositoryImpl
import com.memcoach.offline.data.repository.CardRepositoryImpl
import com.memcoach.offline.data.repository.DeckRepositoryImpl
import com.memcoach.offline.data.repository.KidRepositoryImpl
import com.memcoach.offline.data.repository.ReviewRepositoryImpl
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import com.memcoach.offline.domain.repository.CardRepository
import com.memcoach.offline.domain.repository.DeckRepository
import com.memcoach.offline.domain.repository.KidRepository
import com.memcoach.offline.domain.repository.ReviewRepository

class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    val database: MemCoachDatabase by lazy {
        MemCoachRoomMigrations.requireCompleteChain()
        Room.databaseBuilder(appContext, MemCoachDatabase::class.java, "memcoach-offline.db")
            .addMigrations(*MemCoachRoomMigrations.all.toTypedArray())
            .build()
    }

    val appPreferencesRepository: AppPreferencesRepository by lazy {
        AppPreferencesRepositoryImpl(appContext)
    }

    val kidRepository: KidRepository by lazy {
        KidRepositoryImpl(database.kidDao())
    }

    val deckRepository: DeckRepository by lazy {
        DeckRepositoryImpl(database.deckDao())
    }

    val cardRepository: CardRepository by lazy {
        CardRepositoryImpl(database.cardDao())
    }

    val reviewRepository: ReviewRepository by lazy {
        ReviewRepositoryImpl(
            database = database,
            cardDao = database.cardDao(),
            cardProgressDao = database.cardProgressDao(),
            reviewDao = database.reviewDao(),
        )
    }
}
