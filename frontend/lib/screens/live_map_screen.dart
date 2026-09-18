import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/api_service.dart';

class LiveMapScreen extends StatefulWidget {
  const LiveMapScreen({super.key});

  @override
  State<LiveMapScreen> createState() => _LiveMapScreenState();
}

class _LiveMapScreenState extends State<LiveMapScreen> {
  final MapController _mapController = MapController();
  Timer? _timer;
  List<dynamic> activeBuses = [];
  bool isLoading = true;

  final Map<String, Color> busColors = {
    'BUS-01': const Color(0xFF10B981),
    'BUS-02': const Color(0xFF3B82F6),
    'BUS-03': const Color(0xFFF59E0B),
  };

  @override
  void initState() {
    super.initState();
    _fetchBuses();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _fetchBuses());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchBuses() async {
    final buses = await ApiService.getActiveBuses();
    if (mounted) {
      setState(() {
        activeBuses = buses;
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final markers = <Marker>[];

    for (var bus in activeBuses) {
      final loc = bus['location'];
      if (loc != null && loc['latitude'] != null && (loc['latitude'] as num) > 0) {
        final lat = (loc['latitude'] as num).toDouble();
        final lng = (loc['longitude'] as num).toDouble();
        final busNum = bus['bus_number'] ?? 'BUS';
        final color = busColors[busNum] ?? const Color(0xFF10B981);

        markers.add(
          Marker(
            point: LatLng(lat, lng),
            width: 50,
            height: 50,
            child: GestureDetector(
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('$busNum - Driver: ${bus['driver_name']} (Speed: ${loc['speed']} km/h)'),
                    backgroundColor: color,
                  ),
                );
              },
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2.5),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 8, offset: const Offset(0, 4)),
                  ],
                ),
                child: const Icon(Icons.directions_bus_rounded, color: Colors.white, size: 28),
              ),
            ),
          ),
        );
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Live Campus Bus Map', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF10B981)),
            onPressed: _fetchBuses,
          ),
        ],
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: const MapOptions(
              initialCenter: LatLng(13.3000, 74.7600),
              initialZoom: 12.5,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.smartbus.app',
              ),
              MarkerLayer(markers: markers),
            ],
          ),

          // Active Telemetry Card Overlay
          Positioned(
            bottom: 24,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B).withOpacity(0.95),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF334155)),
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 10)],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _statItem('ACTIVE BUSES', '${markers.length} Active', const Color(0xFF10B981)),
                  _statItem('SYNC INTERVAL', '2 seconds', const Color(0xFF38BDF8)),
                  _statItem('SYSTEM STATUS', 'ONLINE', const Color(0xFFF59E0B)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _statItem(String label, String value, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 10, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.w900)),
      ],
    );
  }
}
