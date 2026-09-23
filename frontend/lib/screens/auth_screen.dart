import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/firebase_auth_service.dart';
import 'driver_dashboard_screen.dart';
import 'student_main_screen.dart';
import 'parent_portal_screen.dart';

enum AuthMode { signIn, signUp, forgotPassword, parentRegistration }

class AuthScreen extends StatefulWidget {
  final String userType;

  const AuthScreen({super.key, this.userType = 'DRIVER'});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  AuthMode _authMode = AuthMode.signIn;

  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _registrationTokenController = TextEditingController();

  final FirebaseAuthService _authService = FirebaseAuthService();

  bool isLoading = false;
  bool _isPasswordVisible = false;
  String? statusMessage;
  bool isError = false;
  String _parentRelationship = 'FATHER';
  String? _registrationToken;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _registrationTokenController.dispose();
    super.dispose();
  }

  void _showMessage(String msg, {bool error = false}) {
    setState(() {
      statusMessage = msg;
      isError = error;
      isLoading = false;
    });
  }

  
  Future<void> _verifyRegistrationToken() async {
    final token = _registrationTokenController.text.trim();
    if (token.isEmpty) return _showMessage('Please enter your registration token.', error: true);
    
    setState(() { isLoading = true; statusMessage = 'Verifying token...'; });
    try {
      final res = await ApiService.verifyParentRequest(token);
      if (res['success'] == true) {
        if (res['data']['status'] != 'APPROVED') {
          _showMessage('This request is ${res['data']['status']}. It must be APPROVED by the student first.', error: true);
          return;
        }
        setState(() {
          _registrationToken = token;
          _authMode = AuthMode.parentRegistration;
          statusMessage = null;
          isLoading = false;
        });
      } else {
        _showMessage(res['error']?.toString() ?? 'Invalid token.', error: true);
      }
    } catch (e) {
      _showMessage(e.toString(), error: true);
    }
  }

  Future<void> _handleBackendVerification() async {
    // 1. Hit FastAPI to sync and verify role
    setState(() => statusMessage = 'Checking account...');
    
    final res = await ApiService.syncUser();
    
    if (res['success'] == true) {
      final user = res['data']?['user'];
      if (user == null) {
        await _authService.signOut();
        _showMessage('Invalid account data received.', error: true);
        return;
      }
      
      final role = user['role'];
      final status = user['status'];
      
      if (status == 'INACTIVE') {
        await _authService.signOut();
        _showMessage('Your Parent account is currently inactive. Please contact the administrator.', error: true);
        return;
      }
      
      // Role mismatch check
      if (role != widget.userType && role != 'ADMIN') {
        await _authService.signOut();
        _showMessage('Role mismatch: You cannot log in as ${widget.userType} using a $role account.', error: true);
        return;
      }
      
      if (role == 'DRIVER') {
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const DriverDashboardScreen()),
          );
        }
      } else if (role == 'STUDENT') {
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const StudentMainScreen()),
          );
        }
      } else if (role == 'PARENT') {
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const ParentPortalScreen()),
          );
        }
      } else {
        await _authService.signOut();
        _showMessage('You are not authorized to access this application.', error: true);
      }
    } else {
      await _authService.signOut();
      if (res['code'] == 'STUDENT_EMAIL_DOMAIN_NOT_ALLOWED' && widget.userType == 'PARENT') {
        _showMessage('Parent account not found. Please complete Parent registration first.', error: true);
      } else {
        _showMessage(res['error']?.toString() ?? 'Unable to connect to SMARTBUS.', error: true);
      }
    }
  }

  Future<void> _submitAuth() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();
    
    // ── PARENT ACCESS REQUEST (Step 1 — no password, no Firebase) ──
    if (widget.userType == 'PARENT' && _authMode == AuthMode.signUp) {
      // Validate student email only
      if (email.isEmpty) {
        return _showMessage("Please enter the student's institutional email.", error: true);
      }
      if (!email.endsWith('@sode-edu.in')) {
        return _showMessage('Please use the student\'s institutional email (@sode-edu.in).', error: true);
      }
      
      setState(() { isLoading = true; statusMessage = 'Sending request...'; isError = false; });
      try {
        final res = await ApiService.submitParentRequest(email, _parentRelationship);
        if (res['success'] == true) {
          _showMessage(
            'Request Sent ✓\n\nYour parent access request has been sent to the student.\n\nAsk the student to open SMARTBUS and approve your request.\n\nYou can complete your Parent account after approval.',
            error: false,
          );
        } else {
          final errorMsg = res['detail']?.toString() ?? res['error']?.toString() ?? 'Failed to send request.';
          _showMessage(errorMsg, error: true);
        }
      } catch (e) {
        _showMessage(e.toString(), error: true);
      }
      return;
    }

    // ── PARENT ACCOUNT CREATION (Step 2 — after student approval) ──
    if (_authMode == AuthMode.parentRegistration) {
      if (_registrationToken == null) {
        return _showMessage('No approved registration token found.', error: true);
      }
      final name = _nameController.text.trim();
      if (name.isEmpty) return _showMessage('Please enter your full name.', error: true);
      if (email.isEmpty) return _showMessage('Please enter your personal email address.', error: true);
      if (password.isEmpty || password.length < 6) return _showMessage('Password must be at least 6 characters.', error: true);
      
      setState(() { isLoading = true; statusMessage = 'Creating Firebase account...'; });
      try {
        final authRes = await _authService.signUpWithEmail(email, password, name);
        if (authRes['success'] != true) {
          return _showMessage(authRes['error']?.toString() ?? 'Failed to create account.', error: true);
        }
        
        setState(() { statusMessage = 'Syncing account with SMARTBUS...'; });
        final idToken = await _authService.getIdToken(true);
        
        // Call backend register
        final res = await ApiService.registerParentAccount(idToken!, _registrationToken!, name);
        if (res['success'] == true) {
          // Force refresh again to pull down custom claims!
          final newToken = await _authService.getIdToken(true);
          if (newToken != null) {
            await ApiService.persistToken(newToken);
          }
          _showMessage('Parent account created successfully.', error: false);
          
          if (mounted) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => const ParentPortalScreen()),
            );
          }
        } else {
          // Delete firebase account since sync failed
          await _authService.deleteCurrentUser();
          _showMessage(res['error']?.toString() ?? 'Registration failed.', error: true);
        }
      } catch (e) {
        _showMessage(e.toString(), error: true);
      }
      return;
    }

    // ── FORGOT PASSWORD ──
    if (email.isEmpty) return _showMessage('Please enter an email address.', error: true);

    if (_authMode == AuthMode.forgotPassword) {
      setState(() {
        isLoading = true;
        statusMessage = 'Sending reset link...';
        isError = false;
      });
      final res = await _authService.resetPassword(email);
      if (res['success'] == true) {
        _showMessage('Password reset link sent to $email');
      } else {
        _showMessage(res['error'], error: true);
      }
      return;
    }
    
    // ── STANDARD SIGN IN / SIGN UP (Student, Driver) ──
    if (password.isEmpty) return _showMessage('Please enter a password.', error: true);
    
    setState(() {
      isLoading = true;
      statusMessage = _authMode == AuthMode.signIn ? 'Signing in...' : 'Creating account...';
      isError = false;
    });
    
    Map<String, dynamic> res;
    if (_authMode == AuthMode.signUp) {
      final name = _nameController.text.trim();
      if (name.isEmpty) return _showMessage('Please enter your full name.', error: true);
      res = await _authService.signUpWithEmail(email, password, name);
    } else {
      res = await _authService.signInWithEmail(email, password);
    }
    
    if (res['success'] == true) {
      await _handleBackendVerification();
    } else {
      _showMessage(res['error'], error: true);
    }
  }

  Future<void> _handleGoogleSignIn() async {
    setState(() {
      isLoading = true;
      statusMessage = 'Signing in with Google...';
      isError = false;
    });

    final res = await _authService.signInWithGoogle();
    if (res['success'] == true) {
      await _handleBackendVerification();
    } else {
      _showMessage(res['error'], error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Slate 900
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Logo placeholder
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: const BoxDecoration(
                    color: Color(0xFF1E293B),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.directions_bus, size: 64, color: Color(0xFF10B981)), // Emerald 500
                ),
                const SizedBox(height: 24),
                
                const Text(
                  'SMARTBUS',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: 1.5),
                ),
                const SizedBox(height: 8),
                
                Text(
                  _authMode == AuthMode.forgotPassword 
                    ? 'Reset your password'
                    : widget.userType == 'STUDENT' ? 'Student Portal' : widget.userType == 'PARENT' ? 'Parent Portal' : 'Driver Portal',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 48),

                                if (_authMode == AuthMode.parentRegistration) ...[
                  if (_registrationToken == null) ...[
                    const Text('Complete Registration\nEnter your approved registration token.', textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                    const SizedBox(height: 16),
                    _inputField('Registration Token', _registrationTokenController, Icons.vpn_key),
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 52,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                        onPressed: isLoading ? null : _verifyRegistrationToken,
                        child: isLoading ? const CircularProgressIndicator(color: Colors.white) : const Text('VERIFY TOKEN', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 1.5)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Align(
                      alignment: Alignment.center,
                      child: TextButton(
                        onPressed: () => setState(() {
                          _authMode = AuthMode.signUp;
                          statusMessage = null;
                        }),
                        child: const Text('Back to Request Access', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                      ),
                    ),
                  ] else ...[
                    const Text('Your request has been approved.\nCreate your Parent account to continue.', textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF10B981), fontSize: 14, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),
                    _inputField('Full Name', _nameController, Icons.person_outline),
                    const SizedBox(height: 16),
                    _inputField('Your Personal Email', _emailController, Icons.email_outlined),
                    const SizedBox(height: 16),
                    _inputField('Password', _passwordController, Icons.lock_outline, isPassword: true),
                    const SizedBox(height: 16),
                    // We re-use the main submit button at the bottom for CREATE ACCOUNT
                  ],
                ] else if (widget.userType == 'PARENT' && _authMode == AuthMode.signUp) ...[
                  const Text('Request Parent Access\nEnter the student\'s institutional email.', textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                  const SizedBox(height: 16),
                  _inputField('Student Email Address', _emailController, Icons.email_outlined),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFF334155)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _parentRelationship,
                        dropdownColor: const Color(0xFF1E293B),
                        style: const TextStyle(color: Colors.white, fontSize: 16),
                        icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF94A3B8)),
                        isExpanded: true,
                        items: ['FATHER', 'MOTHER', 'GUARDIAN', 'OTHER'].map((String value) {
                          return DropdownMenuItem<String>(
                            value: value,
                            child: Text(value),
                          );
                        }).toList(),
                        onChanged: (newValue) {
                          setState(() {
                            _parentRelationship = newValue!;
                          });
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ] else ...[
                  if (_authMode == AuthMode.signUp) ...[
                    _inputField('Full Name', _nameController, Icons.person_outline),
                    const SizedBox(height: 16),
                  ],
                  _inputField('Email Address', _emailController, Icons.email_outlined),
                  const SizedBox(height: 16),
                  if (_authMode == AuthMode.signIn || _authMode == AuthMode.signUp)
                    _inputField('Password', _passwordController, Icons.lock_outline, isPassword: true),
                ],

                if (_authMode == AuthMode.signIn)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => setState(() {
                        _authMode = AuthMode.forgotPassword;
                        statusMessage = null;
                      }),
                      child: const Text('Forgot Password?', style: TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                  )
                else 
                  const SizedBox(height: 20),

                if ((widget.userType == 'STUDENT' || widget.userType == 'PARENT') && _authMode != AuthMode.forgotPassword)
                  Align(
                    alignment: Alignment.center,
                    child: TextButton(
                      onPressed: () => setState(() {
                        _authMode = _authMode == AuthMode.signIn ? AuthMode.signUp : AuthMode.signIn;
                        statusMessage = null;
                      }),
                      child: Text(
                        _authMode == AuthMode.signIn ? "Don't have an account? Sign Up" : 'Back to Sign In',
                        style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),

                if (widget.userType == 'PARENT' && _authMode == AuthMode.signIn)
                  Align(
                    alignment: Alignment.center,
                    child: TextButton(
                      onPressed: () => setState(() {
                        _authMode = AuthMode.parentRegistration;
                        statusMessage = null;
                        _registrationToken = null;
                        _registrationTokenController.clear();
                      }),
                      child: const Text(
                        "Have an approved token? Complete Registration",
                        style: TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),


                if (statusMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isError ? Colors.red.withValues(alpha: 0.1) : const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: isError ? Colors.red : const Color(0xFF10B981)),
                    ),
                    child: Text(
                      statusMessage!,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: isError ? Colors.redAccent : const Color(0xFF34D399), 
                        fontSize: 13, 
                        fontWeight: FontWeight.bold
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],

                                if (!(_authMode == AuthMode.parentRegistration && _registrationToken == null))
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
                        ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Color(0xFF0F172A), strokeWidth: 3))
                        : Text(
                            _authMode == AuthMode.signIn
                                ? 'Sign In'
                                : _authMode == AuthMode.parentRegistration
                                    ? 'Create Account'
                                    : (widget.userType == 'PARENT' && _authMode == AuthMode.signUp)
                                        ? 'Send Request'
                                        : _authMode == AuthMode.signUp
                                            ? 'Sign Up'
                                            : 'Send Reset Link',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                  ),
                ),

                const SizedBox(height: 20),

                if (_authMode == AuthMode.signIn || (_authMode == AuthMode.signUp && widget.userType != 'PARENT')) ...[
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

                  SizedBox(
                    height: 52,
                    child: OutlinedButton.icon(
                      onPressed: isLoading ? null : _handleGoogleSignIn,
                      icon: Image.asset('assets/images/google_logo.png', height: 24),
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

                if (_authMode == AuthMode.forgotPassword)
                  TextButton(
                    onPressed: () => setState(() {
                      _authMode = AuthMode.signIn;
                      statusMessage = null;
                    }),
                    child: const Text('Back to Sign In', style: TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.bold)),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _inputField(String label, TextEditingController controller, IconData icon, {bool isPassword = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          obscureText: isPassword ? !_isPasswordVisible : false,
          keyboardType: label.contains('Email') ? TextInputType.emailAddress : TextInputType.text,
          style: const TextStyle(color: Colors.white, fontSize: 14),
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: const Color(0xFF64748B), size: 20),
            suffixIcon: isPassword 
              ? IconButton(
                  icon: Icon(_isPasswordVisible ? Icons.visibility_off : Icons.visibility, color: const Color(0xFF64748B), size: 20),
                  onPressed: () => setState(() => _isPasswordVisible = !_isPasswordVisible),
                )
              : null,
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
