import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DriverControlsScreen extends StatefulWidget {
  const DriverControlsScreen({super.key});

  @override
  State<DriverControlsScreen> createState() => _DriverControlsScreenState();
}

class _DriverControlsScreenState extends State<DriverControlsScreen> {
  final TextEditingController _latController = TextEditingController(text: '13.3418');
  final TextEditingController _lngController = TextEditingController(text: '74.7473');
  final TextEditingController _speedController = TextEditingController(text: '42.5');

  bool isAutoDriving = false;
  Timer? _autoDriveTimer;
  int _routeIndex = 0;
  List<String> logs = [];

  final List<Map<String, dynamic>> routePoints = [
    {'name': 'Udupi Bus Stand', 'lat': 13.3418, 'lng': 74.7473},
    {'name': 'Kalsanka Junction', 'lat': 13.3445, 'lng': 74.7540},
    {'name': 'Gundibail', 'lat': 13.3480, 'lng': 74.7610},
    {'name': 'Kunjibettu', 'lat': 13.3512, 'lng': 74.7690},
    {'name': 'Indrali Station', 'lat': 13.3550, 'lng': 74.7780},
    {'name': 'SMVITM Campus', 'lat': 13.2541, 'lng': 74.7865},
  ];

  @override
  void dispose() {
    _autoDriveTimer?.cancel();
    _latController.dispose();
    _lngController.dispose();
    _speedController.dispose();
    super.dispose();
  }

  Future<void> _sendPing() async {
    final lat = double.tryParse(_latController.text) ?? 13.3418;
    final lng = double.tryParse(_lngController.text) ?? 74.7473;
    final speed = double.tryParse(_speedController.text) ?? 40.0;

    final res = await ApiService.ingestGps(
      latitude: lat,
      longitude: lng,
      speed: speed,
    );

    final timestamp = DateTime.now().toIso8601String().substring(11, 19);
    setState(() {
      logs.insert(0, '[$timestamp] Ping ($lat, $lng, $speed km/h) -> ${res['success'] == true ? 'SUCCESS' : 'FAILED'}');
    });
  }

  void _toggleAutoDrive() {
    if (isAutoDriving) {
      _autoDriveTimer?.cancel();
      setState(() => isAutoDriving = false);
    } else {
      setState(() => isAutoDriving = true);
      _autoDriveTimer = Timer.periodic(const Duration(seconds: 2), (_) {
        final pt = routePoints[_routeIndex];
        _latController.text = pt['lat'].toString();
        _lngController.text = pt['lng'].toString();
        _sendPing();
        _routeIndex = (_routeIndex + 1) % routePoints.length;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Driver GPS Controls', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Manual GPS Ingestion', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(child: _inputField('Latitude', _latController)),
                const SizedBox(width: 12),
                Expanded(child: _inputField('Longitude', _lngController)),
                const SizedBox(width: 12),
                Expanded(child: _inputField('Speed (km/h)', _speedController)),
              ],
            ),

            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _sendPing,
                    icon: const Icon(Icons.send_rounded),
                    label: const Text('Send Manual Ping'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: const Color(0xFF0F172A),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _toggleAutoDrive,
                    icon: Icon(isAutoDriving ? Icons.pause_rounded : Icons.play_arrow_rounded),
                    label: Text(isAutoDriving ? 'Pause Route' : 'Auto-Drive Route'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isAutoDriving ? const Color(0xFFF59E0B) : const Color(0xFF3B82F6),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),
            const Text('Telemetry Log Stream', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),

            Expanded(
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF020617),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: ListView.builder(
                  itemCount: logs.length,
                  itemBuilder: (context, index) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2.0),
                      child: Text(
                        logs[index],
                        style: const TextStyle(color: Color(0xFF38BDF8), fontFamily: 'monospace', fontSize: 12),
                      ),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _inputField(String label, TextEditingController controller) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            filled: true,
            fillColor: const Color(0xFF1E293B),
            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF334155))),
          ),
        ),
      ],
    );
  }
}
