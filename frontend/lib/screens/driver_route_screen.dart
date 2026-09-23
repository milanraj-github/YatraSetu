import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class DriverRouteScreen extends StatefulWidget {
  final Map<String, dynamic> trackingData;

  const DriverRouteScreen({super.key, required this.trackingData});

  @override
  State<DriverRouteScreen> createState() => _DriverRouteScreenState();
}

class _DriverRouteScreenState extends State<DriverRouteScreen> {
  List<dynamic> _stops = [];
  bool _hasMissingCoordinates = false;
  LatLng? _busLocation;

  @override
  void initState() {
    super.initState();
    _processRouteData();
  }

  void _processRouteData() {
    if (widget.trackingData['route'] != null &&
        widget.trackingData['route']['stops'] != null) {
      _stops = widget.trackingData['route']['stops'];
      
      // Sort by sequence_order to be safe
      _stops.sort((a, b) => (a['sequence_order'] ?? 0).compareTo(b['sequence_order'] ?? 0));

      for (var stop in _stops) {
        if (stop['latitude'] == 0.0 && stop['longitude'] == 0.0) {
          _hasMissingCoordinates = true;
          break;
        }
      }
    }
    
    // In Phase D4/D5, we will pull live bus location here.
    // For now, no location is drawn natively until GPS is wired in.
  }

  @override
  Widget build(BuildContext context) {
    final routeName = widget.trackingData['route']?['name'] ?? 'Unknown Route';
    final busName = widget.trackingData['bus']?['bus_number'] ?? 'Unknown Bus';
    final currentStop = _stops.isNotEmpty ? _stops.first['name'] : 'None';
    final nextStop = _stops.length > 1 ? _stops[1]['name'] : 'None';

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: Text('← Route ($busName)', style: const TextStyle(color: Colors.white, fontSize: 16)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: Column(
        children: [
          // Header Info
          Container(
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B),
            width: double.infinity,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(routeName, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Current Stop:', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                        Text(currentStop, style: const TextStyle(color: Color(0xFF0284C7), fontSize: 14, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('Next Stop:', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                        Text(nextStop, style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 14, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Row(
                  children: [
                    Text('GPS: ', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                    Text('🟢 Connected', style: TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.bold)),
                  ],
                ),
              ],
            ),
          ),
          
          if (_hasMissingCoordinates)
            Container(
              padding: const EdgeInsets.all(12),
              color: const Color(0xFF7F1D1D),
              width: double.infinity,
              child: const Row(
                children: [
                  Icon(Icons.warning_amber_rounded, color: Colors.white),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Missing verified coordinates for some stops. The route line cannot be drawn accurately.',
                      style: TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),

          // Map Area
          Expanded(
            child: _hasMissingCoordinates 
              ? _buildStopListOnly() 
              : _buildMap(),
          ),
        ],
      ),
    );
  }

  // If we don't have valid coordinates for the stops, we just show a list for now
  Widget _buildStopListOnly() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _stops.length,
      itemBuilder: (context, index) {
        final stop = _stops[index];
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0),
          child: Row(
            children: [
              const Icon(Icons.location_on, color: Color(0xFF38BDF8), size: 20),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  stop['name'] ?? 'Unknown',
                  style: const TextStyle(color: Colors.white, fontSize: 16),
                ),
              ),
              if (stop['latitude'] == 0.0)
                const Text('[NO DATA]', style: TextStyle(color: Color(0xFFEF4444), fontSize: 12, fontWeight: FontWeight.bold)),
            ],
          ),
        );
      },
    );
  }

  Widget _buildMap() {
    if (_stops.isEmpty) {
      return const Center(child: Text('No stops available on this route.', style: TextStyle(color: Colors.white)));
    }

    final points = _stops.map((s) => LatLng(s['latitude'], s['longitude'])).toList();
    // Default to Udupi general area if empty
    final center = points.isNotEmpty ? points.first : const LatLng(13.340881, 74.742142);

    return FlutterMap(
      options: MapOptions(
        initialCenter: center,
        initialZoom: 13.0,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.smartbus.app',
        ),
        PolylineLayer(
          polylines: [
            Polyline(
              points: points,
              strokeWidth: 4.0,
              color: const Color(0xFF3B82F6),
            ),
          ],
        ),
        MarkerLayer(
          markers: _stops.map((s) {
            return Marker(
              point: LatLng(s['latitude'], s['longitude']),
              width: 40,
              height: 40,
              child: const Icon(Icons.location_on, color: Color(0xFFEF4444), size: 30),
            );
          }).toList(),
        ),
        if (_busLocation != null)
          MarkerLayer(
            markers: [
              Marker(
                point: _busLocation!,
                width: 50,
                height: 50,
                child: const Icon(Icons.directions_bus, color: Color(0xFF10B981), size: 40),
              )
            ],
          ),
      ],
    );
  }
}
