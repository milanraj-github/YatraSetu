import 'package:flutter/material.dart';
import '../services/firebase_auth_service.dart';
import 'auth_screen.dart';
import 'student_parent_requests_screen.dart';

class StudentProfileScreen extends StatelessWidget {
  final Map<String, dynamic> studentData;
  final FirebaseAuthService _authService = FirebaseAuthService();

  StudentProfileScreen({super.key, required this.studentData});

  Future<void> _handleLogout(BuildContext context) async {
    await _authService.signOut();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const SizedBox(height: 16),
            const CircleAvatar(
              radius: 40,
              backgroundColor: Color(0xFF334155),
              child: Icon(Icons.school, size: 50, color: Colors.white),
            ),
            const SizedBox(height: 24),
            
            const Align(
              alignment: Alignment.centerLeft,
              child: Text("MY PROFILE", style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
            ),
            const SizedBox(height: 12),
            
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF334155), width: 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildInfoRow('Name', studentData['full_name'] ?? 'Unknown', Icons.badge),
                  const Divider(color: Color(0xFF334155), height: 32),
                  _buildInfoRow('Email', studentData['email'] ?? 'No email', Icons.email),
                  const Divider(color: Color(0xFF334155), height: 32),
                  _buildInfoRow('Role', studentData['role'] ?? 'STUDENT', Icons.security, color: Colors.blueAccent),
                  const Divider(color: Color(0xFF334155), height: 32),
                  _buildInfoRow(
                    'Status', 
                    studentData['status'] ?? 'UNKNOWN', 
                    Icons.verified_user, 
                    color: studentData['status'] == 'ACTIVE' ? Colors.greenAccent : Colors.redAccent
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const StudentParentRequestsScreen()),
                  );
                },
                icon: const Icon(Icons.family_restroom, color: Colors.white),
                label: const Text('PARENT REQUESTS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF38BDF8),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => _handleLogout(context),
                icon: const Icon(Icons.logout, color: Colors.white),
                label: const Text('LOGOUT', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.redAccent,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, IconData icon, {Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: Colors.white54, size: 16),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12, letterSpacing: 1.0)),
          ],
        ),
        const SizedBox(height: 6),
        Text(value, style: TextStyle(color: color ?? Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
