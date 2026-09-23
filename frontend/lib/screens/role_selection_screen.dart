import 'package:flutter/material.dart';
import 'auth_screen.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  void _navigateToAuth(BuildContext context, String userType) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AuthScreen(userType: userType),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 48.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(
                  color: Color(0xFF1E293B),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.directions_bus, size: 64, color: Color(0xFF10B981)),
              ),
              const SizedBox(height: 24),
              const Text(
                'Welcome to SMARTBUS',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 8),
              const Text(
                'Please select your role to continue',
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 16),
              ),
              const Spacer(),
              Expanded(
                flex: 4,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      _buildRoleCard(
                        context,
                        title: 'Student',
                        subtitle: 'Live tracking, ETA, and routes',
                        icon: Icons.school,
                        color: const Color(0xFF38BDF8),
                        onTap: () => _navigateToAuth(context, 'STUDENT'),
                      ),
                      const SizedBox(height: 20),
                      _buildRoleCard(
                        context,
                        title: 'Driver',
                        subtitle: 'Route navigation and trip management',
                        icon: Icons.local_shipping,
                        color: const Color(0xFF10B981),
                        onTap: () => _navigateToAuth(context, 'DRIVER'),
                      ),
                      const SizedBox(height: 20),
                      _buildRoleCard(
                        context,
                        title: 'Parent',
                        subtitle: 'Track your child\'s bus, ETA, and safety',
                        icon: Icons.family_restroom,
                        color: const Color(0xFFF59E0B),
                        onTap: () => _navigateToAuth(context, 'PARENT'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRoleCard(BuildContext context, {required String title, required String subtitle, required IconData icon, required Color color, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: (0.5)), width: 2),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: color.withValues(alpha: (0.1)), shape: BoxShape.circle),
              child: Icon(icon, color: color, size: 32),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, color: Color(0xFF64748B), size: 16),
          ],
        ),
      ),
    );
  }
}
