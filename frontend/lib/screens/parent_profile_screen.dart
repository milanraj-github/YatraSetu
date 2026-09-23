import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/firebase_auth_service.dart';
import 'auth_screen.dart';

class ParentProfileScreen extends StatefulWidget {
  final Map<String, dynamic>? initialProfile;
  final List<dynamic> students;

  const ParentProfileScreen({super.key, this.initialProfile, required this.students});

  @override
  State<ParentProfileScreen> createState() => _ParentProfileScreenState();
}

class _ParentProfileScreenState extends State<ParentProfileScreen> {
  final FirebaseAuthService _authService = FirebaseAuthService();
  bool _isLoading = false;
  Map<String, dynamic>? _profile;

  @override
  void initState() {
    super.initState();
    _profile = widget.initialProfile;
    _refreshProfile();
  }

  Future<void> _refreshProfile() async {
    setState(() => _isLoading = true);
    final res = await ApiService.getMe();
    if (mounted) {
      if (res['success'] == true) {
        setState(() => _profile = res['data']);
      }
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleLogout(BuildContext context) async {
    await _authService.signOut();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  Future<void> _handlePasswordReset() async {
    if (_profile == null || _profile!['email'] == null) return;
    final email = _profile!['email'];
    
    // Show loading
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sending reset email...')));
    
    final res = await _authService.resetPassword(email);
    if (!mounted) return;
    
    if (res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Password reset email sent to $email'), backgroundColor: Colors.green));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['error'] ?? 'Error'), backgroundColor: Colors.red));
    }
  }

  Future<void> _showEditNameDialog() async {
    final TextEditingController controller = TextEditingController(text: _profile?['full_name'] ?? '');
    
    final result = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Edit Name', style: TextStyle(color: Colors.white)),
          content: TextField(
            controller: controller,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Full Name',
              labelStyle: TextStyle(color: Colors.white54),
              enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
              focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.blue)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
              onPressed: () {
                final text = controller.text.trim();
                if (text.isNotEmpty) Navigator.pop(context, text);
              },
              child: const Text('Save', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );

    if (result != null && result != _profile?['full_name']) {
      setState(() => _isLoading = true);
      final res = await ApiService.updateMe(result);
      if (mounted) {
        if (res['success'] == true) {
          setState(() => _profile = res['data']);
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profile updated successfully'), backgroundColor: Colors.green));
        } else {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['error'] ?? 'Failed to update profile'), backgroundColor: Colors.red));
        }
        setState(() => _isLoading = false);
      }
    }
  }

  Widget _buildInfoRow(String label, String value, {Widget? trailing}) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500)),
              ],
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final name = _profile?['full_name'] ?? 'Parent';
    final email = _profile?['email'] ?? '';
    final status = _profile?['status'] ?? 'UNKNOWN';

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Profile & Settings', style: TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: _isLoading && _profile == null
          ? const Center(child: CircularProgressIndicator(color: Colors.blue))
          : RefreshIndicator(
              onRefresh: _refreshProfile,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Center(
                    child: CircleAvatar(
                      radius: 40,
                      backgroundColor: Colors.blue.withValues(alpha: 0.2),
                      child: const Icon(Icons.person, size: 40, color: Colors.blue),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: Text(
                      name,
                      style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                  ),
                  Center(
                    child: Text(
                      email,
                      style: const TextStyle(color: Colors.white70, fontSize: 14),
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text('ACCOUNT', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  const SizedBox(height: 8),
                  _buildInfoRow('Full Name', name, trailing: IconButton(
                    icon: const Icon(Icons.edit, color: Colors.blue),
                    onPressed: _showEditNameDialog,
                  )),
                  _buildInfoRow('Email Address', email),
                  _buildInfoRow('Account Status', status, trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: status == 'ACTIVE' ? Colors.green.withValues(alpha: 0.2) : Colors.red.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      status,
                      style: TextStyle(color: status == 'ACTIVE' ? Colors.green : Colors.red, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  )),
                  const SizedBox(height: 24),
                  const Text('LINKED STUDENTS', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  const SizedBox(height: 8),
                  if (widget.students.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 8),
                      child: Text('No active linked students.', style: TextStyle(color: Colors.white54)),
                    ),
                  ...widget.students.map((s) => _buildInfoRow('Student', s['student']['full_name'], trailing: const Icon(Icons.check_circle, color: Colors.green))),
                  const SizedBox(height: 24),
                  const Text('SECURITY', style: TextStyle(color: Colors.white54, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  const SizedBox(height: 8),
                  ListTile(
                    tileColor: const Color(0xFF1E293B),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    leading: const Icon(Icons.lock_reset, color: Colors.orange),
                    title: const Text('Reset Password', style: TextStyle(color: Colors.white)),
                    subtitle: const Text('Send password reset email', style: TextStyle(color: Colors.white54)),
                    onTap: _handlePasswordReset,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: () => _handleLogout(context),
                    icon: const Icon(Icons.logout, color: Colors.white),
                    label: const Text('Logout', style: TextStyle(color: Colors.white, fontSize: 16)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red.withValues(alpha: 0.8),
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }
}
