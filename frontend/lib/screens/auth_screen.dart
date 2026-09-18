import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'live_map_screen.dart';
import 'driver_controls_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  String selectedUserKey = 'driver1';
  bool isLoading = false;
  Map<String, dynamic>? syncResponse;

  final Map<String, Map<String, String>> users = {
    'driver1': {'name': 'Driver One', 'email': 'driver1@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-01'},
    'driver2': {'name': 'Driver Two', 'email': 'driver2@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-02'},
    'driver3': {'name': 'Driver Three', 'email': 'driver3@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-03'},
    'student1': {'name': 'Student One', 'email': 'student1@sode-edu.in', 'role': 'STUDENT', 'bus': 'N/A'},
    'admin1': {'name': 'Admin One', 'email': 'admin1@sode-edu.in', 'role': 'ADMIN', 'bus': 'All Buses'},
  };

  Future<void> _handleLoginSync() async {
    setState(() {
      isLoading = true;
    });

    ApiService.currentRole = selectedUserKey;
    final res = await ApiService.syncUser();

    setState(() {
      isLoading = false;
      syncResponse = res;
    });

    if (mounted && res['success'] == true) {
      final role = users[selectedUserKey]!['role'];
      if (role == 'DRIVER') {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const DriverControlsScreen()),
        );
      } else {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const LiveMapScreen()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = users[selectedUserKey]!;

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Auth & Role Switcher', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Select User Identity',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text(
              'Simulate Firebase Authentication Token Login',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
            const SizedBox(height: 20),

            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: selectedUserKey,
                  dropdownColor: const Color(0xFF1E293B),
                  isExpanded: true,
                  items: users.entries.map((entry) {
                    return DropdownMenuItem<String>(
                      value: entry.key,
                      child: Text(
                        '${entry.value['name']} (${entry.value['role']})',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                      ),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => selectedUserKey = val);
                  },
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Profile Preview Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  _infoRow('Name:', user['name']!),
                  _infoRow('Email:', user['email']!),
                  _infoRow('Role:', user['role']!),
                  _infoRow('Assigned Bus:', user['bus']!),
                ],
              ),
            ),

            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: isLoading ? null : _handleLoginSync,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: const Color(0xFF0F172A),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: isLoading
                    ? const CircularProgressIndicator(color: Color(0xFF0F172A))
                    : const Text('Authenticate & Sync Backend Session', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
              ),
            ),

            const SizedBox(height: 24),

            if (syncResponse != null) ...[
              const Text('Backend Response:', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF020617),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: SingleChildScrollView(
                    child: Text(
                      syncResponse.toString(),
                      style: const TextStyle(color: Color(0xFF34D399), fontFamily: 'monospace', fontSize: 12),
                    ),
                  ),
                ),
              ),
            ] else const Spacer(),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
          Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
        ],
      ),
    );
  }
}
