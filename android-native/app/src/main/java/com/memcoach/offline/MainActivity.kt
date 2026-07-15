package com.memcoach.offline

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.memcoach.offline.di.AppContainer
import com.memcoach.offline.ui.MemCoachApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val appContainer = AppContainer(applicationContext)
        setContent {
            MemCoachApp(appContainer = appContainer)
        }
    }
}
