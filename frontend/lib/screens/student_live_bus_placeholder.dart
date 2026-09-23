import 'package:flutter/material.dart';

class StudentLiveBusPlaceholder extends StatelessWidget {
  const StudentLiveBusPlaceholder({super.key});

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
              Icon(Icons.location_off, size: 80, color: Colors.white24),
              SizedBox(height: 24),
              Text(
                'LIVE BUS',
                style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1.5),
              ),
              SizedBox(height: 16),
              Text(
                'Your assigned bus will appear here.\n\nLive tracking will be available once your bus assignment is configured.',
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
