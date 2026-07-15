package com.memcoach.offline.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.memcoach.offline.di.AppContainer
import com.memcoach.offline.feature.cards.CardsScreen
import com.memcoach.offline.feature.cards.CardsViewModel
import com.memcoach.offline.feature.home.HomeEvent
import com.memcoach.offline.feature.home.HomeScreen
import com.memcoach.offline.feature.home.HomeViewModel
import com.memcoach.offline.feature.home.homeViewModelFactory
import com.memcoach.offline.feature.review.ReviewEvent
import com.memcoach.offline.feature.review.ReviewScreen
import com.memcoach.offline.feature.review.ReviewViewModel
import com.memcoach.offline.feature.settings.SettingsScreen
import com.memcoach.offline.feature.settings.SettingsViewModel

@Composable
fun MemCoachApp(appContainer: AppContainer) {
    val navController = rememberNavController()

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            NavHost(
                navController = navController,
                startDestination = AppRoutes.HOME,
                modifier = Modifier.safeDrawingPadding(),
            ) {
                composable(route = AppRoutes.HOME) {
                    val viewModel: HomeViewModel = viewModel(
                        factory = homeViewModelFactory(
                            appPreferencesRepository = appContainer.appPreferencesRepository,
                            kidRepository = appContainer.kidRepository,
                            deckRepository = appContainer.deckRepository,
                            cardRepository = appContainer.cardRepository,
                        ),
                    )
                    val state by viewModel.state.collectAsState()

                    LaunchedEffect(viewModel) {
                        viewModel.events.collect { event ->
                            when (event) {
                                is HomeEvent.NavigateToSettings -> {
                                    navController.navigate(AppRoutes.SETTINGS)
                                }
                                is HomeEvent.NavigateToCards -> {
                                    navController.navigate(AppRoutes.cards(event.deckId))
                                }
                                is HomeEvent.NavigateToReview -> {
                                    navController.navigate(AppRoutes.review(event.kidId, event.deckId))
                                }
                            }
                        }
                    }

                    HomeScreen(
                        state = state,
                        onKidNameChange = viewModel::onKidNameChanged,
                        onAddKid = viewModel::addKid,
                        onDeckNameChange = viewModel::onDeckNameChanged,
                        onAddDeck = viewModel::addDeck,
                        onParentPinChange = viewModel::onParentPinChanged,
                        onUnlockParentMode = viewModel::unlockParentMode,
                        onOpenSettings = viewModel::openSettings,
                        onSelectKid = viewModel::selectKid,
                        onSelectDeck = viewModel::selectDeck,
                        onOpenCards = viewModel::openCards,
                        onStartReview = viewModel::startReview,
                    )
                }

                composable(route = AppRoutes.SETTINGS) {
                    val viewModel: SettingsViewModel = viewModel(
                        factory = SettingsViewModel.factory(
                            appPreferencesRepository = appContainer.appPreferencesRepository,
                        ),
                    )
                    val state by viewModel.state.collectAsState()

                    SettingsScreen(
                        state = state,
                        onPinChange = viewModel::onPinChanged,
                        onSavePin = viewModel::savePin,
                        onClearPin = viewModel::clearPin,
                        onSetChildMode = viewModel::setChildMode,
                        onBack = { navController.popBackStack() },
                    )
                }

                composable(
                    route = AppRoutes.CARDS,
                    arguments = listOf(navArgument("deckId") { type = NavType.LongType }),
                ) { backStackEntry ->
                    val deckId = backStackEntry.arguments?.getLong("deckId") ?: return@composable
                    val viewModel: CardsViewModel = viewModel(
                        factory = CardsViewModel.factory(
                            deckId = deckId,
                            cardRepository = appContainer.cardRepository,
                            deckRepository = appContainer.deckRepository,
                        ),
                    )
                    val state by viewModel.state.collectAsState()

                    CardsScreen(
                        state = state,
                        onPromptChange = viewModel::onPromptChanged,
                        onFullTextChange = viewModel::onFullTextChanged,
                        onAddCard = viewModel::addCard,
                        onBack = { navController.popBackStack() },
                    )
                }

                composable(
                    route = AppRoutes.REVIEW,
                    arguments = listOf(
                        navArgument("kidId") { type = NavType.LongType },
                        navArgument("deckId") { type = NavType.LongType },
                    ),
                ) { backStackEntry ->
                    val kidId = backStackEntry.arguments?.getLong("kidId") ?: return@composable
                    val deckId = backStackEntry.arguments?.getLong("deckId") ?: return@composable
                    val viewModel: ReviewViewModel = viewModel(
                        factory = ReviewViewModel.factory(
                            kidId = kidId,
                            deckId = deckId,
                            reviewRepository = appContainer.reviewRepository,
                            deckRepository = appContainer.deckRepository,
                        ),
                    )
                    val state by viewModel.state.collectAsState()

                    LaunchedEffect(viewModel) {
                        viewModel.events.collect { event ->
                            when (event) {
                                is ReviewEvent.Exit -> navController.popBackStack()
                            }
                        }
                    }

                    ReviewScreen(
                        state = state,
                        onAnswerChange = viewModel::onAnswerChanged,
                        onSubmit = viewModel::submit,
                        onRefresh = viewModel::refresh,
                        onBack = viewModel::goBack,
                    )
                }
            }
        }
    }
}
