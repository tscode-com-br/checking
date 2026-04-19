package com.br.checkingnative.data.migration

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.data.preferences.CheckingStateRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LegacyFlutterMigrationCoordinator @Inject constructor(
    @param:ApplicationContext private val context: Context,
    private val checkingStateRepository: CheckingStateRepository,
) {
    suspend fun assessAutomaticMigrationAvailability(): LegacyFlutterMigrationReport {
        val sourceAppInstalled = isSourceAppInstalled()
        val report = if (sourceAppInstalled) {
            LegacyFlutterMigrationReport(
                status = LegacyFlutterMigrationStatus.MANUAL_ONBOARDING_REQUIRED,
                message = "O app Flutter foi detectado com o package " +
                    "${LegacyFlutterStorageContract.sourceApplicationId}, " +
                    "mas o app Kotlin e separado e nao pode ler o sandbox interno dele. " +
                    "Prossiga com onboarding manual: informe a chave novamente, " +
                    "conceda as permissoes e sincronize os dados pela API.",
                sourceAppInstalled = true,
            )
        } else {
            LegacyFlutterMigrationReport(
                status = LegacyFlutterMigrationStatus.SOURCE_APP_NOT_INSTALLED,
                message = "Nenhuma instalacao ativa de " +
                    "${LegacyFlutterStorageContract.sourceApplicationId} " +
                    "foi detectada neste dispositivo. O app Kotlin deve seguir " +
                    "com onboarding manual.",
                sourceAppInstalled = false,
            )
        }

        checkingStateRepository.updateLegacyMigrationReport(report)
        return report
    }

    @Suppress("DEPRECATION")
    private fun isSourceAppInstalled(): Boolean {
        return try {
            val packageManager = context.packageManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getPackageInfo(
                    LegacyFlutterStorageContract.sourceApplicationId,
                    PackageManager.PackageInfoFlags.of(0),
                )
            } else {
                packageManager.getPackageInfo(
                    LegacyFlutterStorageContract.sourceApplicationId,
                    0,
                )
            }
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }
    }
}
