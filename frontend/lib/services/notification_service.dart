import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'api_service.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  
  Function(RemoteMessage)? onMessageReceived;

  Future<void> initialize() async {
    NotificationSettings settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      String? token = await _fcm.getToken();
      if (token != null) {
        await _registerToken(token);
      }

      _fcm.onTokenRefresh.listen((newToken) {
        _registerToken(newToken);
      });

      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        if (onMessageReceived != null) {
          onMessageReceived!(message);
        }
      });
    }
  }

  Future<void> _registerToken(String token) async {
    String platform = Platform.isIOS ? 'ios' : 'android';
    await ApiService.registerDeviceToken(token, platform: platform);
  }

  Future<void> deactivate() async {
    String? token = await _fcm.getToken();
    if (token != null) {
      await ApiService.deactivateDeviceToken(token);
    }
  }
}
