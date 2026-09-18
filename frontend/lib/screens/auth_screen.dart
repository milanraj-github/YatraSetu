import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'live_map_screen.dart';
import 'driver_controls_screen.dart';

enum AuthMode { signIn, signUp, forgotPassword }

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  AuthMode _authMode = AuthMode.signIn;

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController(text: 'driver1@sode-edu.in');
  final TextEditingController _passwordController = TextEditingController(text: 'password123');
  final TextEditingController _confirmPasswordController = TextEditingController();

  String selectedRoleKey = 'driver1';
  bool isLoading = false;
  String? statusMessage;

  final Map<String, Map<String, String>> users = {
    'driver1': {'name': 'Driver One', 'email': 'driver1@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-01'},
    'driver2': {'name': 'Driver Two', 'email': 'driver2@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-02'},
    'driver3': {'name': 'Driver Three', 'email': 'driver3@sode-edu.in', 'role': 'DRIVER', 'bus': 'BUS-03'},
    'student1': {'name': 'Student One', 'email': 'student1@sode-edu.in', 'role': 'STUDENT', 'bus': 'N/A'},
    'admin1': {'name': 'Admin One', 'email': 'admin1@sode-edu.in', 'role': 'ADMIN', 'bus': 'All Buses'},
  };

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submitAuth() async {
    setState(() {
      isLoading = true;
      statusMessage = null;
    });

    // Match input email to role key if standard test emails are used
    final matchingEntry = users.entries.firstWhere(
      (e) => e.value['email']?.toLowerCase() == _emailController.text.trim().toLowerCase(),
      orElse: () => MapEntry(selectedRoleKey, users[selectedRoleKey]!),
    );

    ApiService.currentRole = matchingEntry.key;

    if (_authMode == AuthMode.forgotPassword) {
      await Future.delayed(const Duration(milliseconds: 1000));
      setState(() {
        isLoading = false;
        statusMessage = 'Password reset link sent to ${_emailController.text}!';
      });
      return;
    }

    final res = await ApiService.syncUser();

    setState(() {
      isLoading = false;
    });

    if (mounted && res['success'] == true) {
      final role = matchingEntry.value['role'];
      if (role == 'DRIVER') {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const DriverControlsScreen()),
        );
      } else {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const LiveMapScreen()),
        );
      }
    } else {
      setState(() {
        statusMessage = res['error']?.toString() ?? 'Authentication failed.';
      });
    }
  }

  Future<void> _handleGoogleSignIn() async {
    setState(() {
      isLoading = true;
    });

    // Simulate Google Sign-In with student profile
    ApiService.currentRole = 'student1';
    final res = await ApiService.syncUser();

    setState(() {
      isLoading = false;
    });

    if (mounted && res['success'] == true) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LiveMapScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header Logo & Title
                const Icon(Icons.directions_bus_rounded, color: Color(0xFF10B981), size: 48),
                const SizedBox(height: 12),
                Text(
                  _authMode == AuthMode.signIn
                      ? 'Welcome Back'
                      : _authMode == AuthMode.signUp
                          ? 'Create Account'
                          : 'Reset Password',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                Text(
                  _authMode == AuthMode.signIn
                      ? 'Sign in to access YatraSetu tracking'
                      : _authMode == AuthMode.signUp
                          ? 'Register for college bus services'
                          : 'Enter your email to receive recovery link',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                ),
                const SizedBox(height: 24),

                // Quick Preset Identity Switcher Card
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Demo Preset Account Selector:',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: selectedRoleKey,
                          dropdownColor: const Color(0xFF1E293B),
                          isExpanded: true,
                          items: users.entries.map((entry) {
                            return DropdownMenuItem<String>(
                              value: entry.key,
                              child: Text(
                                '${entry.value['name']} (${entry.value['role']}) - ${entry.value['email']}',
                                style: const TextStyle(color: Color(0xFF34D399), fontSize: 13, fontWeight: FontWeight.w600),
                              ),
                            );
                          }).toList(),
                          onChanged: (val) {
                            if (val != null) {
                              setState(() {
                                selectedRoleKey = val;
                                _emailController.text = users[val]!['email']!;
                              });
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                // Full Name Input (Sign Up Only)
                if (_authMode == AuthMode.signUp) ...[
                  _inputField('Full Name', _nameController, Icons.person_rounded),
                  const SizedBox(height: 14),
                ],

                // Email Address Input
                _inputField('Email Address', _emailController, Icons.email_rounded),
                const SizedBox(height: 14),

                // Password Input (Sign In & Sign Up Only)
                if (_authMode != AuthMode.forgotPassword) ...[
                  _inputField('Password', _passwordController, Icons.lock_rounded, obscureText: true),
                  const SizedBox(height: 14),
                ],

                // Confirm Password Input (Sign Up Only)
                if (_authMode == AuthMode.signUp) ...[
                  _inputField('Confirm Password', _confirmPasswordController, Icons.lock_outline_rounded, obscureText: true),
                  const SizedBox(height: 14),
                ],

                // Forgot Password Link (Sign In Only)
                if (_authMode == AuthMode.signIn)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => setState(() => _authMode = AuthMode.forgotPassword),
                      child: const Text('Forgot Password?', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                  ),

                const SizedBox(height: 10),

                // Status message alert if any
                if (statusMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF10B981)),
                    ),
                    child: Text(
                      statusMessage!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFF34D399), fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],

                // Primary Submit Button
                SizedBox(
                  height: 52,
                  child: ElevatedButton(
                    onPressed: isLoading ? null : _submitAuth,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: const Color(0xFF0F172A),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: isLoading
                        ? const CircularProgressIndicator(color: Color(0xFF0F172A))
                        : Text(
                            _authMode == AuthMode.signIn
                                ? 'Sign In'
                                : _authMode == AuthMode.signUp
                                    ? 'Create Account'
                                    : 'Send Reset Link',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                  ),
                ),

                const SizedBox(height: 20),

                // Divider with text "OR"
                if (_authMode == AuthMode.signIn || _authMode == AuthMode.signUp) ...[
                  const Row(
                    children: [
                      Expanded(child: Divider(color: Color(0xFF334155))),
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 12),
                        child: Text('OR', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                      Expanded(child: Divider(color: Color(0xFF334155))),
                    ],
                  ),

                  const SizedBox(height: 20),

                  // Google Sign In Button
                  SizedBox(
                    height: 52,
                    child: OutlinedButton.icon(
                      onPressed: isLoading ? null : _handleGoogleSignIn,
                      icon: Image.network(
                        'https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg',
                        height: 22,
                        errorBuilder: (_, __, ___) => const Icon(Icons.g_mobiledata_rounded, color: Colors.white, size: 28),
                      ),
                      label: const Text('Continue with Google', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Color(0xFF334155)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        backgroundColor: const Color(0xFF1E293B),
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 24),

                // Mode Switcher Footer Links
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _authMode == AuthMode.signIn
                          ? "Don't have an account?"
                          : _authMode == AuthMode.signUp
                              ? "Already have an account?"
                              : "Remembered your password?",
                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                    ),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          _authMode = (_authMode == AuthMode.signIn) ? AuthMode.signUp : AuthMode.signIn;
                          statusMessage = null;
                        });
                      },
                      child: Text(
                        _authMode == AuthMode.signIn
                            ? 'Sign Up'
                            : _authMode == AuthMode.signUp
                                ? 'Sign In'
                                : 'Back to Sign In',
                        style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _inputField(String label, TextEditingController controller, IconData icon, {bool obscureText = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          obscureText: obscureText,
          style: const TextStyle(color: Colors.white, fontSize: 14),
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: const Color(0xFF64748B), size: 20),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: Color(0xFF334155)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: Color(0xFF10B981)),
            ),
          ),
        ),
      ],
    );
  }
}
