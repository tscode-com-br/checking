package com.br.checkingnative.data.legacy

object LegacyFlutterStorageContract {
    const val sourceApplicationId: String = "com.br.checking"

    const val statePrefsKey: String = "checking_flutter_state_v1"
    const val secureApiSharedKey: String = "checking_flutter_api_shared_key"
    const val prefsApiSharedKeyBackup: String =
        "checking_flutter_api_shared_key_backup_v1"
    const val initialAndroidSetupPromptedKey: String =
        "checking_flutter_initial_android_setup_prompted_v1"

    const val locationsDatabaseName: String = "checking_locations.db"
    const val locationsTableName: String = "locations"
    const val locationsCachePrefsKey: String = "checking_locations_catalog_cache_v1"
}
