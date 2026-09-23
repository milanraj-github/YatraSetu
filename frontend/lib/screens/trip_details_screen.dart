import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class TripDetailsScreen extends StatelessWidget {
  final Map<String, dynamic> trip;

  const TripDetailsScreen({super.key, required this.trip});

  @override
  Widget build(BuildContext context) {
    final route = trip['route'];
    final bus = trip['bus'];
    final session = trip['session'];
    final schedule = trip['schedule'];
    final stops = route?['stops'] as List<dynamic>? ?? [];
    
    // Calculate bounding box for map
    final List<LatLng> stopPoints = [];
    for (var s in stops) {
      final bp = s['boarding_point'];
      if (bp != null) {
        stopPoints.add(LatLng(bp['latitude'], bp['longitude']));
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Trip Details'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      backgroundColor: const Color(0xFF0F172A),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                children: [
                  _buildDetailRow('Route Name', route?['name'] ?? 'Unknown', Icons.route),
                  const Divider(color: Color(0xFF334155), height: 24),
                  _buildDetailRow('Direction', session?['direction'] ?? 'UNKNOWN', Icons.swap_horiz),
                  const Divider(color: Color(0xFF334155), height: 24),
                  _buildDetailRow('Bus', bus?['bus_number'] ?? 'Unknown', Icons.directions_bus),
                  const Divider(color: Color(0xFF334155), height: 24),
                  _buildDetailRow('Start Time', _formatTime(session?['started_at'] ?? schedule?['start_time']), Icons.play_circle_outline),
                  const Divider(color: Color(0xFF334155), height: 24),
                  _buildDetailRow('End Time', _formatTime(session?['ended_at'] ?? schedule?['end_time']), Icons.stop_circle_outlined),
                  const Divider(color: Color(0xFF334155), height: 24),
                  _buildDetailRow('Status', session?['status'] ?? 'COMPLETED', Icons.info_outline, color: Colors.green),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const Text('Route Stops', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: stops.map((s) {
                  final bp = s['boarding_point'];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12.0),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 12,
                          backgroundColor: Colors.blue.withValues(alpha: 0.2),
                          child: Text('${s['sequence_order']}', style: const TextStyle(color: Colors.blue, fontSize: 12)),
                        ),
                        const SizedBox(width: 12),
                        Text(bp?['name'] ?? 'Unknown Stop', style: const TextStyle(color: Colors.white, fontSize: 15)),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 24),
            if (stopPoints.isNotEmpty) ...[
              const Text('Route Map', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Container(
                height: 200,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: FlutterMap(
                    options: MapOptions(
                      initialCenter: stopPoints.first,
                      initialZoom: 12,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.example.app',
                      ),
                      MarkerLayer(
                        markers: stopPoints.map((pt) => Marker(
                          point: pt,
                          width: 30,
                          height: 30,
                          child: const Icon(Icons.location_on, color: Colors.red, size: 30),
                        )).toList(),
                      ),
                      PolylineLayer(
                        polylines: [
                          Polyline(
                            points: stopPoints,
                            color: Colors.blue,
                            strokeWidth: 4,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ]
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, IconData icon, {Color? color}) {
    return Row(
      children: [
        Icon(icon, color: Colors.white54, size: 20),
        const SizedBox(width: 12),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 14)),
        const Spacer(),
        Text(value, style: TextStyle(color: color ?? Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
      ],
    );
  }

  String _formatTime(String? timeStr) {
    if (timeStr == null) return 'N/A';
    final parsed = DateTime.tryParse(timeStr);
    if (parsed != null) {
      return "${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}";
    }
    if (timeStr.length > 5) return timeStr.substring(0, 5);
    return timeStr;
  }
}
