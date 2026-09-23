import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'screens/splash_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(const SmartBusApp());
}

class SmartBusApp extends StatelessWidget {
  const SmartBusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'YatraSetu / SMARTBUS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF10B981),
          surface: Color(0xFF1E293B),
        ),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}
