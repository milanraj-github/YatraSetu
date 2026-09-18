import 'dart:math' as math;
import 'package:flutter/material.dart';

/// 3D Isometric Animated Bus Painter rendered on Canvas
class Animated3DBusPainter extends CustomPainter {
  final double animationValue; // 0.0 to 1.0 continuously
  final double pulseValue;     // 0.0 to 1.0 glow effect

  Animated3DBusPainter({
    required this.animationValue,
    required this.pulseValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2 - 20);

    // 1. Draw Road with Animated 3D Lane Markers
    _drawRoad(canvas, size, center);

    // 2. Draw Ground Shadow with Breathing Pulse
    _drawShadow(canvas, center);

    // 3. Draw Engine Under-Glow Aura
    _drawEngineGlow(canvas, center);

    // 4. Draw 3D Bus Body (Isometric Perspective)
    _drawBusBody(canvas, center);

    // 5. Draw 3D Windows & Windshield
    _drawWindows(canvas, center);

    // 6. Draw Headlights with Dynamic Light Beams
    _drawHeadlights(canvas, center);

    // 7. Draw Revolving 3D Alloy Wheels with Spoke Rotations
    _draw3DWheels(canvas, center);

    // 8. Draw Front LED Grille & Badge
    _drawFrontGrille(canvas, center);
  }

  void _drawRoad(Canvas canvas, Size size, Offset center) {
    final roadPaint = Paint()
      ..color = const Color(0xFF1E293B)
      ..style = PaintingStyle.fill;

    final roadPath = Path()
      ..moveTo(center.dx - 180, center.dy + 90)
      ..lineTo(center.dx + 180, center.dy + 30)
      ..lineTo(center.dx + 220, center.dy + 140)
      ..lineTo(center.dx - 140, center.dy + 200)
      ..close();

    canvas.drawPath(roadPath, roadPaint);

    // Animated dashed lines along road
    final dashPaint = Paint()
      ..color = const Color(0xFF38BDF8).withOpacity(0.6)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    final offset = animationValue * 40;
    for (int i = 0; i < 6; i++) {
      final t1 = (i * 0.2 + offset / 200) % 1.0;
      final t2 = (t1 + 0.08) % 1.0;

      final startX = center.dx - 140 + t1 * 320;
      final startY = center.dy + 145 - t1 * 50;

      final endX = center.dx - 140 + t2 * 320;
      final endY = center.dy + 145 - t2 * 50;

      canvas.drawLine(Offset(startX, startY), Offset(endX, endY), dashPaint);
    }
  }

  void _drawShadow(Canvas canvas, Offset center) {
    final shadowScale = 1.0 + pulseValue * 0.05;
    final shadowPaint = Paint()
      ..color = Colors.black.withOpacity(0.5 - pulseValue * 0.1)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18);

    final shadowRect = RRect.fromLTRBR(
      center.dx - 120 * shadowScale,
      center.dy + 65,
      center.dx + 110 * shadowScale,
      center.dy + 115,
      const Radius.circular(30),
    );
    canvas.drawRRect(shadowRect, shadowPaint);
  }

  void _drawEngineGlow(Canvas canvas, Offset center) {
    final glowPaint = Paint()
      ..color = const Color(0xFF10B981).withOpacity(0.3 + pulseValue * 0.3)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 25);

    canvas.drawCircle(Offset(center.dx + 40, center.dy + 75), 45, glowPaint);
  }

  void _drawBusBody(Canvas canvas, Offset center) {
    // Top Side (Roof)
    final roofPaint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFF34D399), Color(0xFF059669)],
      ).createShader(Rect.fromLTWH(center.dx - 100, center.dy - 70, 200, 40));

    final roofPath = Path()
      ..moveTo(center.dx - 60, center.dy - 70) // Top Left
      ..lineTo(center.dx + 60, center.dy - 90)  // Top Right
      ..lineTo(center.dx + 120, center.dy - 50) // Front Roof Corner
      ..lineTo(center.dx, center.dy - 30)      // Center Roof
      ..close();

    canvas.drawPath(roofPath, roofPaint);

    // Left Side (Long Side Panel)
    final sidePaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xFF059669), Color(0xFF047857), Color(0xFF064E3B)],
      ).createShader(Rect.fromLTWH(center.dx - 100, center.dy - 50, 160, 120));

    final sidePath = Path()
      ..moveTo(center.dx - 60, center.dy - 70)
      ..lineTo(center.dx, center.dy - 30)
      ..lineTo(center.dx, center.dy + 60)
      ..lineTo(center.dx - 60, center.dy + 20)
      ..close();

    canvas.drawPath(sidePath, sidePaint);

    // Front Side (Front Face Panel)
    final frontPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF10B981), Color(0xFF059669), Color(0xFF022C22)],
      ).createShader(Rect.fromLTWH(center.dx, center.dy - 50, 140, 130));

    final frontPath = Path()
      ..moveTo(center.dx, center.dy - 30)
      ..lineTo(center.dx + 120, center.dy - 50)
      ..lineTo(center.dx + 120, center.dy + 40)
      ..lineTo(center.dx, center.dy + 60)
      ..close();

    canvas.drawPath(frontPath, frontPaint);

    // 3D Bevel Highlights
    final highlightPaint = Paint()
      ..color = Colors.white.withOpacity(0.3)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    canvas.drawPath(roofPath, highlightPaint);
    canvas.drawLine(Offset(center.dx, center.dy - 30), Offset(center.dx, center.dy + 60), highlightPaint);
  }

  void _drawWindows(Canvas canvas, Offset center) {
    // Glass Tint Shader
    final glassPaint = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFFBAE6FD), Color(0xFF0284C7)],
      ).createShader(Rect.fromLTWH(center.dx, center.dy - 40, 100, 50));

    // Front Windshield
    final windshield = Path()
      ..moveTo(center.dx + 10, center.dy - 22)
      ..lineTo(center.dx + 110, center.dy - 42)
      ..lineTo(center.dx + 110, center.dy + 5)
      ..lineTo(center.dx + 10, center.dy + 20)
      ..close();

    canvas.drawPath(windshield, glassPaint);

    // Glass Reflection Shininess
    final shinePaint = Paint()
      ..color = Colors.white.withOpacity(0.6)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    canvas.drawLine(
      Offset(center.dx + 30, center.dy - 15),
      Offset(center.dx + 90, center.dy - 25),
      shinePaint,
    );

    // Side Windows (3 Windows in perspective)
    for (int i = 0; i < 3; i++) {
      final startX = center.dx - 52 + (i * 16);
      final sideWindow = Path()
        ..moveTo(startX, center.dy - 55 + (i * 5))
        ..lineTo(startX + 12, center.dy - 51 + (i * 5))
        ..lineTo(startX + 12, center.dy - 15 + (i * 5))
        ..lineTo(startX, center.dy - 19 + (i * 5))
        ..close();

      canvas.drawPath(sideWindow, glassPaint);
    }
  }

  void _drawHeadlights(Canvas canvas, Offset center) {
    // Light Beams (Volumetric Light Projection)
    final beamPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          const Color(0xFFFDE047).withOpacity(0.6 + pulseValue * 0.2),
          const Color(0xFFFDE047).withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(center.dx + 110, center.dy + 10, 100, 60));

    final beamPath = Path()
      ..moveTo(center.dx + 115, center.dy + 20)
      ..lineTo(center.dx + 200, center.dy + 45)
      ..lineTo(center.dx + 175, center.dy + 75)
      ..lineTo(center.dx + 115, center.dy + 35)
      ..close();

    canvas.drawPath(beamPath, beamPaint);

    // Dual Headlight Bulbs
    final bulbPaint = Paint()
      ..color = const Color(0xFFFEF08A)
      ..maskFilter = const MaskFilter.blur(BlurStyle.solid, 4);

    canvas.drawCircle(Offset(center.dx + 112, center.dy + 24), 5, bulbPaint);
    canvas.drawCircle(Offset(center.dx + 112, center.dy + 34), 5, bulbPaint);
  }

  void _draw3DWheels(Canvas canvas, Offset center) {
    final tirePaint = Paint()..color = const Color(0xFF0F172A);
    final rimPaint = Paint()..color = const Color(0xFF94A3B8);

    final wheelCenters = [
      Offset(center.dx - 35, center.dy + 42), // Rear Left
      Offset(center.dx + 40, center.dy + 72),  // Front Right
    ];

    final angle = animationValue * math.pi * 4;

    for (final wc in wheelCenters) {
      // Outer Tire
      canvas.drawCircle(wc, 16, tirePaint);
      // Alloy Rim
      canvas.drawCircle(wc, 10, rimPaint);

      // Rotating Spokes
      final spokePaint = Paint()
        ..color = const Color(0xFF334155)
        ..strokeWidth = 2;

      for (int i = 0; i < 4; i++) {
        final currentAngle = angle + (i * math.pi / 2);
        final dx = wc.dx + math.cos(currentAngle) * 8;
        final dy = wc.dy + math.sin(currentAngle) * 8;
        canvas.drawLine(wc, Offset(dx, dy), spokePaint);
      }
    }
  }

  void _drawFrontGrille(Canvas canvas, Offset center) {
    // LED Bumper Line
    final ledPaint = Paint()
      ..color = const Color(0xFF38BDF8)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    canvas.drawLine(
      Offset(center.dx + 10, center.dy + 48),
      Offset(center.dx + 115, center.dy + 32),
      ledPaint,
    );

    // Brand Emblem Badge
    final badgePaint = Paint()..color = const Color(0xFFF59E0B);
    canvas.drawCircle(Offset(center.dx + 65, center.dy + 40), 4, badgePaint);
  }

  @override
  bool shouldRepaint(covariant Animated3DBusPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue ||
        oldDelegate.pulseValue != pulseValue;
  }
}
