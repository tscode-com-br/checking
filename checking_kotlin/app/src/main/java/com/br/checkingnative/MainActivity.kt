package com.br.checkingnative

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.br.checkingnative.ui.BootstrapApp
import com.br.checkingnative.ui.BootstrapViewModel
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val viewModel: BootstrapViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val uiState by viewModel.uiState.collectAsStateWithLifecycle()
            CheckingKotlinTheme {
                BootstrapApp(uiState = uiState)
            }
        }
    }
}

