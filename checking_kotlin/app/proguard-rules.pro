# Android entry points referenced from the manifest.
-keep class com.br.checkingnative.CheckingKotlinApp { *; }
-keep class com.br.checkingnative.MainActivity { *; }
-keep class com.br.checkingnative.CheckingLocationForegroundService { *; }
-keep class com.br.checkingnative.BootCompletedReceiver { *; }
-keep class com.br.checkingnative.NotificationActionReceiver { *; }
-keep class com.br.checkingnative.ScheduledNotificationReceiver { *; }

# Keep annotations and generic signatures used by Hilt, Room and Compose tooling.
-keepattributes RuntimeVisibleAnnotations,RuntimeInvisibleAnnotations,Signature,InnerClasses,EnclosingMethod
