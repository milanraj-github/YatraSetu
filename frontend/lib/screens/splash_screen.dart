import 'package:flutter/material.dart';
import '../widgets/animated_3d_bus.dart';
import 'role_selection_screen.dart';
import 'driver_dashboard_screen.dart';
import 'student_main_screen.dart';
import 'parent_portal_screen.dart';
import '../services/firebase_auth_service.dart';
import '../services/api_service.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with TickerProviderStateMixin {
  late AnimationController _busDriveController;
  late AnimationController _pulseController;
  final FirebaseAuthService _authService = FirebaseAuthService();

  @override
  void initState() {
    super.initState();

    _busDriveController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _checkAuthSession();
  }

  Future<void> _checkAuthSession() async {
    // Wait for animation for a bit
    await Future.delayed(const Duration(milliseconds: 1500));
    
    try {
      final user = await _authService.getCurrentUser();
      if (user != null) {
        final token = await _authService.getIdToken(true);
        if (token != null) {
          await ApiService.persistToken(token);
          final res = await ApiService.syncUser();
          
          if (res['success'] == true) {
            final role = res['data']?['user']?['role'];
            final status = res['data']?['user']?['status'];
            
            if (status == 'INACTIVE') {
              await _authService.signOut();
            } else if (role == 'DRIVER') {
              _navigate(const DriverDashboardScreen());
              return;
            } else if (role == 'STUDENT') {
              _navigate(const StudentMainScreen());
              return;
            } else if (role == 'PARENT') {
              _navigate(const ParentPortalScreen());
              return;
            }
          }
        }
        // If anything fails, sign out
        await _authService.signOut();
      }
    } catch (e) {
      debugPrint('Session restore failed: $e');
    }
    
    _navigate(const RoleSelectionScreen());
  }

  void _navigate(Widget screen) {
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => screen,
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
      ),
    );
  }

  @override
  void dispose() {
    _busDriveController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Stack(
          children: [
            Positioned(
              top: -100,
              right: -100,
              child: Container(
                width: 300,
                height: 300,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                ),
              ),
            ),
            Positioned(
              bottom: -50,
              left: -50,
              child: Container(
                width: 250,
                height: 250,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF0284C7).withValues(alpha: 0.15),
                ),
              ),
            ),
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(),
                AnimatedBuilder(
                  animation: Listenable.merge([_busDriveController, _pulseController]),
                  builder: (context, child) {
                    return SizedBox(
                      width: 340,
                      height: 260,
                      child: CustomPaint(
                        painter: Animated3DBusPainter(
                          animationValue: _busDriveController.value,
                          pulseValue: _pulseController.value,
                        ),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 20),
                Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          'Yatra',
                          style: TextStyle(
                            fontSize: 36,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 1.2,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'Setu',
                            style: TextStyle(
                              fontSize: 36,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF0F172A),
                              letterSpacing: 1.2,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'SMARTBUS Live GPS Tracking & Campus Mobility',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        color: Color(0xFF94A3B8),
                        fontWeight: FontWeight.w500,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                const Padding(
                  padding: EdgeInsets.only(bottom: 32.0),
                  child: CircularProgressIndicator(
                    color: Color(0xFF10B981),
                    strokeWidth: 3,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
