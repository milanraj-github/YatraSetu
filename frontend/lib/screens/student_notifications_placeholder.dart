import 'package:flutter/material.dart';

class StudentNotificationsPlaceholder extends StatelessWidget {
  const StudentNotificationsPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFF0F172A),
      body: Center(
        child: Padding(
          padding: EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.notifications_off, size: 80, color: Colors.white24),
              SizedBox(height: 24),
              Text(
                'NOTIFICATIONS',
                style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1.5),
              ),
              SizedBox(height: 16),
              Text(
                'No notifications yet.\n\nBus and travel notifications will appear here when available.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white54, fontSize: 16, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
