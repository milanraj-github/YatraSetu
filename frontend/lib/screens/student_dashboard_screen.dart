import 'package:flutter/material.dart';

class StudentDashboardScreen extends StatelessWidget {
  final Map<String, dynamic>? student;
  final Map<String, dynamic>? bus;
  final Future<void> Function() onRefresh;

  const StudentDashboardScreen({super.key, required this.student, this.bus, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: onRefresh,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Good Morning, ${student?['full_name'] ?? 'Student'} 👋',
              style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('Student Dashboard', style: TextStyle(color: Colors.white54, fontSize: 16)),
            const SizedBox(height: 32),
            
            _buildSectionCard(
              'MY BUS',
              bus != null 
                  ? 'Bus Number: ${bus!['bus_number']}\nRegistration: ${bus!['registration_number']}\nStatus: ${bus!['status']}'
                  : 'No bus assigned yet.',
              Icons.directions_bus,
              Colors.orangeAccent
            ),
            
            const SizedBox(height: 16),
            
            _buildSectionCard(
              'LIVE BUS',
              'Live tracking will appear here.',
              Icons.location_on,
              Colors.blueAccent
            ),

            const SizedBox(height: 16),
            
            _buildSectionCard(
              'TODAY',
              'No bus schedule available.',
              Icons.calendar_today,
              Colors.greenAccent
            ),
            
            const SizedBox(height: 16),
            
            _buildSectionCard(
              'NOTIFICATIONS',
              'No new notifications.',
              Icons.notifications,
              Colors.grey
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionCard(String title, String subtitle, IconData icon, Color iconColor) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: iconColor.withValues(alpha: 0.2),
            radius: 24,
            child: Icon(icon, color: iconColor, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                const SizedBox(height: 6),
                Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
