package com.memcoach.offline.feature.cards

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

@Composable
fun CardsScreen(
    state: CardsUiState,
    onPromptChange: (String) -> Unit,
    onFullTextChange: (String) -> Unit,
    onAddCard: () -> Unit,
    onBack: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = onBack) { Text("Back") }
            Text("Cards: ${state.deckName}", style = MaterialTheme.typography.headlineSmall)
        }

        OutlinedTextField(
            value = state.promptInput,
            onValueChange = onPromptChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Prompt") },
            singleLine = true,
        )

        OutlinedTextField(
            value = state.fullTextInput,
            onValueChange = onFullTextChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Full text") },
            minLines = 3,
        )

        Button(onClick = onAddCard) {
            Text("Add Card")
        }

        state.statusMessage?.let { message ->
            Text(message)
        }

        Text("Current cards", style = MaterialTheme.typography.titleMedium)
        if (state.cards.isEmpty()) {
            Text("No cards yet")
        } else {
            state.cards.forEach { card ->
                Column(modifier = Modifier.fillMaxWidth()) {
                    Text(text = card.prompt, style = MaterialTheme.typography.titleSmall)
                    Text(
                        text = card.fullText,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        text = "Due ${card.dueDate} | Int ${card.intervalDays} | EF ${"%.2f".format(card.easeFactor)}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
