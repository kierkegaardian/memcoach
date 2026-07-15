package com.memcoach.offline.feature.settings

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
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen(
    state: SettingsUiState,
    onPinChange: (String) -> Unit,
    onSavePin: () -> Unit,
    onClearPin: () -> Unit,
    onSetChildMode: (Boolean) -> Unit,
    onBack: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = onBack) { Text("Back") }
            Text("Device Settings", style = MaterialTheme.typography.headlineSmall)
        }

        Text(
            text = "These settings make a shared Android device safer to hand to a child.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Child mode", style = MaterialTheme.typography.titleMedium)
                Text(
                    text = "Hide parent setup behind a PIN and keep the device focused on review.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Switch(
                checked = state.childModeEnabled,
                onCheckedChange = onSetChildMode,
            )
        }

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Parent PIN", style = MaterialTheme.typography.titleMedium)
            Text(
                text =
                    if (state.hasParentPin) {
                        "A PIN is currently set."
                    } else {
                        "Set a local PIN before enabling child mode on a kid's device."
                    },
                style = MaterialTheme.typography.bodyMedium,
            )
            OutlinedTextField(
                value = state.pinInput,
                onValueChange = onPinChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Parent PIN") },
                visualTransformation = PasswordVisualTransformation(),
                singleLine = true,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = onSavePin) { Text("Save PIN") }
                Button(onClick = onClearPin, enabled = state.hasParentPin) { Text("Clear PIN") }
            }
        }

        state.statusMessage?.let { message ->
            Text(message, style = MaterialTheme.typography.bodyMedium)
        }
    }
}
