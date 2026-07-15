package com.memcoach.offline.feature.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.memcoach.offline.domain.model.Deck
import com.memcoach.offline.domain.model.Kid

@Composable
fun HomeScreen(
    state: HomeUiState,
    onKidNameChange: (String) -> Unit,
    onAddKid: () -> Unit,
    onDeckNameChange: (String) -> Unit,
    onAddDeck: () -> Unit,
    onParentPinChange: (String) -> Unit,
    onUnlockParentMode: () -> Unit,
    onOpenSettings: () -> Unit,
    onSelectKid: (Long) -> Unit,
    onSelectDeck: (Long) -> Unit,
    onOpenCards: () -> Unit,
    onStartReview: () -> Unit,
) {
    val parentLocked = state.childModeEnabled && !state.isParentUnlocked

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("MemCoach Offline", style = MaterialTheme.typography.headlineMedium)

        ReviewLaunchCard(
            state = state,
            onOpenSettings = onOpenSettings,
            onStartReview = onStartReview,
        )

        if (parentLocked) {
            ParentUnlockCard(
                state = state,
                onParentPinChange = onParentPinChange,
                onUnlockParentMode = onUnlockParentMode,
            )
        } else {
            ParentSetupSection(
                state = state,
                onKidNameChange = onKidNameChange,
                onAddKid = onAddKid,
                onDeckNameChange = onDeckNameChange,
                onAddDeck = onAddDeck,
                onSelectKid = onSelectKid,
                onSelectDeck = onSelectDeck,
                onOpenCards = onOpenCards,
            )
        }

        state.statusMessage?.let { message ->
            Text(text = message, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun ReviewLaunchCard(
    state: HomeUiState,
    onOpenSettings: () -> Unit,
    onStartReview: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Child Review", style = MaterialTheme.typography.titleLarge)
            Text(
                text =
                    if (state.childModeEnabled) {
                        "This device is in child mode. Parent setup stays behind the PIN."
                    } else {
                        "Choose a kid and deck, then launch review. Enable child mode in settings before handing the device over."
                    },
                style = MaterialTheme.typography.bodyMedium,
            )
            Text("Kid: ${state.kids.firstOrNull { it.id == state.selectedKidId }?.name ?: "Not selected"}")
            Text("Deck: ${state.decks.firstOrNull { it.id == state.selectedDeckId }?.name ?: "Not selected"}")
            if (state.selectedDeckId != null && state.selectedDeckCardCount == 0) {
                Text("Add at least one card to this deck before starting review.")
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = onStartReview, enabled = state.canStartReview) {
                    Text("Start Review")
                }
                Button(onClick = onOpenSettings) {
                    Text("Settings")
                }
            }
        }
    }
}

@Composable
private fun ParentUnlockCard(
    state: HomeUiState,
    onParentPinChange: (String) -> Unit,
    onUnlockParentMode: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Parent Unlock", style = MaterialTheme.typography.titleLarge)
            Text(
                text =
                    if (state.hasParentPin) {
                        "Enter the local parent PIN to edit kids, decks, or cards."
                    } else {
                        "No parent PIN is set yet. Open settings from an unlocked session and add one before deploying this to a child."
                    },
                style = MaterialTheme.typography.bodyMedium,
            )
            OutlinedTextField(
                value = state.parentPinInput,
                onValueChange = onParentPinChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Parent PIN") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
            )
            Button(onClick = onUnlockParentMode) {
                Text("Unlock Parent Mode")
            }
        }
    }
}

@Composable
private fun ParentSetupSection(
    state: HomeUiState,
    onKidNameChange: (String) -> Unit,
    onAddKid: () -> Unit,
    onDeckNameChange: (String) -> Unit,
    onAddDeck: () -> Unit,
    onSelectKid: (Long) -> Unit,
    onSelectDeck: (Long) -> Unit,
    onOpenCards: () -> Unit,
) {
    Text("Parent Setup", style = MaterialTheme.typography.titleLarge)

    EntryBlock(
        title = "Kids",
        inputValue = state.kidNameInput,
        inputLabel = "Kid name",
        buttonLabel = "Add Kid",
        onInputChange = onKidNameChange,
        onAdd = onAddKid,
    )

    SelectableList(
        label = "Select kid",
        items = state.kids,
        selectedId = state.selectedKidId,
        onSelect = onSelectKid,
    )

    EntryBlock(
        title = "Decks",
        inputValue = state.deckNameInput,
        inputLabel = "Deck name",
        buttonLabel = "Add Deck",
        onInputChange = onDeckNameChange,
        onAdd = onAddDeck,
    )

    SelectableDeckList(
        decks = state.decks,
        selectedId = state.selectedDeckId,
        onSelect = onSelectDeck,
    )

    Button(onClick = onOpenCards) {
        Text("Manage Cards")
    }
}

@Composable
private fun EntryBlock(
    title: String,
    inputValue: String,
    inputLabel: String,
    buttonLabel: String,
    onInputChange: (String) -> Unit,
    onAdd: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium)
        OutlinedTextField(
            value = inputValue,
            onValueChange = onInputChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text(inputLabel) },
            singleLine = true,
        )
        Button(onClick = onAdd) {
            Text(buttonLabel)
        }
    }
}

@Composable
private fun SelectableList(
    label: String,
    items: List<Kid>,
    selectedId: Long?,
    onSelect: (Long) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.titleMedium)
        if (items.isEmpty()) {
            Text("No kids yet")
            return
        }
        items.forEach { kid ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelect(kid.id) }
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = selectedId == kid.id, onClick = { onSelect(kid.id) })
                Text(kid.name)
            }
        }
    }
}

@Composable
private fun SelectableDeckList(
    decks: List<Deck>,
    selectedId: Long?,
    onSelect: (Long) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("Select deck", style = MaterialTheme.typography.titleMedium)
        if (decks.isEmpty()) {
            Text("No decks yet")
            return
        }
        decks.forEach { deck ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelect(deck.id) }
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = selectedId == deck.id, onClick = { onSelect(deck.id) })
                Text(deck.name)
            }
        }
    }
}
