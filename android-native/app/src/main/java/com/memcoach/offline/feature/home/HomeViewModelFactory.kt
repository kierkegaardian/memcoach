package com.memcoach.offline.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.memcoach.offline.domain.repository.AppPreferencesRepository
import com.memcoach.offline.domain.repository.CardRepository
import com.memcoach.offline.domain.repository.DeckRepository
import com.memcoach.offline.domain.repository.KidRepository

fun homeViewModelFactory(
    appPreferencesRepository: AppPreferencesRepository,
    kidRepository: KidRepository,
    deckRepository: DeckRepository,
    cardRepository: CardRepository,
): ViewModelProvider.Factory {
    return object : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return HomeViewModel(
                appPreferencesRepository = appPreferencesRepository,
                kidRepository = kidRepository,
                deckRepository = deckRepository,
                cardRepository = cardRepository,
            ) as T
        }
    }
}
