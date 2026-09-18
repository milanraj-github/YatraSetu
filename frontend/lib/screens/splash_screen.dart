import 'package:flutter/material.dart';
import '../widgets/animated_3d_bus.dart';
import 'auth_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _busDriveController;
  late AnimationController _pulseController;

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

    // Auto-navigate to Auth Screen after 2.5 seconds intro animation
    Future.delayed(const Duration(milliseconds: 2500), () {
      if (mounted) {
        _navigateToAuth();
      }
    });
  }

  @override
  void dispose() {
    _busDriveController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  void _navigateToAuth() {
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            const AuthScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Stack(
          children: [
            // Background Ambient Glow Gradients
            Positioned(
              top: -100,
              right: -100,
              child: Container(
                width: 300,
                height: 300,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF10B981).withOpacity(0.15),
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
                  color: const Color(0xFF0284C7).withOpacity(0.15),
                ),
              ),
            ),

            // Content
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(),

                // 3D Animated Bus Canvas Container
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

                // Animated App Title & Subtitle
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
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
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

