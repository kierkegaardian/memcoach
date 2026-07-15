package com.memcoach.offline.feature.review

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
import androidx.compose.ui.unit.dp

@Composable
fun ReviewScreen(
    state: ReviewUiState,
    onAnswerChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onRefresh: () -> Unit,
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
            Text("Review: ${state.deckName}", style = MaterialTheme.typography.headlineSmall)
        }

        when {
            state.isLoading -> Text("Loading...")
            state.currentCard == null -> {
                Text("No due cards.")
                Button(onClick = onRefresh) { Text("Refresh") }
            }
            else -> {
                val card = requireNotNull(state.currentCard)
                Text(card.prompt, style = MaterialTheme.typography.titleMedium)
                Text("Due ${card.dueDate} | Int ${card.intervalDays} | EF ${"%.2f".format(card.easeFactor)}")

                OutlinedTextField(
                    value = state.answerInput,
                    onValueChange = onAnswerChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Type your recall") },
                    minLines = 4,
                )

                Button(
                    onClick = onSubmit,
                    enabled = !state.isSubmitting && state.answerInput.trim().isNotEmpty(),
                ) {
                    Text(if (state.isSubmitting) "Submitting..." else "Submit Review")
                }
            }
        }

        state.lastResult?.let { result ->
            Text(
                text = "Last grade: ${result.grade.name.lowercase()} | next due ${result.nextDueDate}",
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        state.statusMessage?.let { message ->
            Text(message, style = MaterialTheme.typography.bodyMedium)
        }
    }
}
