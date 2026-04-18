package com.br.checkingnative.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.room.Room
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.data.local.db.CheckingDatabase
import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.remote.CheckingHttpTransport
import com.br.checkingnative.data.remote.JdkCheckingHttpTransport
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun providePreferencesDataStore(
        @ApplicationContext context: Context,
    ): DataStore<Preferences> {
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { context.preferencesDataStoreFile("checking_kotlin_prefs") },
        )
    }

    @Provides
    @Singleton
    fun provideCheckingDatabase(
        @ApplicationContext context: Context,
    ): CheckingDatabase {
        return Room.databaseBuilder(
            context,
            CheckingDatabase::class.java,
            LegacyFlutterStorageContract.locationsDatabaseName,
        ).fallbackToDestructiveMigration(dropAllTables = true).build()
    }

    @Provides
    fun provideManagedLocationDao(
        database: CheckingDatabase,
    ): ManagedLocationDao = database.managedLocationDao()

    @Provides
    @Singleton
    fun provideCheckingHttpTransport(): CheckingHttpTransport = JdkCheckingHttpTransport()
}
