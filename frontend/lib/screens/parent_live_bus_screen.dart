import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/api_service.dart';

class ParentLiveBusScreen extends StatefulWidget {
  final int studentId;
  final String studentName;
  const ParentLiveBusScreen({super.key, required this.studentId, required this.studentName});

  @override
  State<ParentLiveBusScreen> createState() => _ParentLiveBusScreenState();
}

class _ParentLiveBusScreenState extends State<ParentLiveBusScreen> {
  Timer? _timer;
  bool _isLoading = true;
  String? _error;
  
  Map<String, dynamic>? _bus;
  Map<String, dynamic>? _location;
  Map<String, dynamic>? _route;
  String? _direction;
  Map<String, dynamic>? _stopIntelligence;
  Map<String, dynamic>? _eta;
  String _trackingStatus = "LOADING";
  
  final MapController _mapController = MapController();
  bool _firstLoad = true;

  @override
  void initState() {
    super.initState();
    _fetchLiveBus();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) {
      _fetchLiveBus();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchLiveBus() async {
    try {
      final res = await ApiService.getParentLiveBus(widget.studentId);
      if (!mounted) return;
      
      if (res['success'] == true && res['data'] != null) {
        final data = res['data'];
        setState(() {
          _isLoading = false;
          _error = null;
          _trackingStatus = data['tracking_status'] ?? 'UNAVAILABLE';
          _bus = data['bus'];
          _location = data['location'];
          _route = data['route'];
          _direction = data['direction'];
          _stopIntelligence = data['stop_intelligence'];
          _eta = data['eta'];
        });
        
        if (_location != null && _firstLoad) {
          _mapController.move(
            LatLng(_location!['latitude'], _location!['longitude']), 
            16.0
          );
          _firstLoad = false;
        }
      } else {
        setState(() {
          _error = res['error'] ?? "Failed to load live tracking";
          _isLoading = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = "Network error. Please try again.";
        _isLoading = false;
      });
    }
  }


  String _getEtaText() {
    if (_eta == null) return "Unavailable";
    final status = _eta!['status'];
    if (status == 'AVAILABLE') {
      final approx = _eta!['approximate'] == true ? '~' : '';
      return '$approx${_eta!['minutes']} min';
    } else if (status == 'ARRIVING') {
      return 'Arriving soon';
    } else if (status == 'ARRIVED') {
      return 'Arrived';
    } else if (status == 'NO_ACTIVE_TRIP') {
      return 'Bus is not currently on an active trip.';
    } else if (status == 'NO_LIVE_LOCATION') {
      return 'ETA unavailable';
    } else if (status == 'STALE') {
      return 'ETA temporarily unavailable';
    } else if (status == 'NO_NEXT_STOP') {
      return 'No upcoming stop';
    } else if (status == 'INSUFFICIENT_DATA') {
      return 'ETA unavailable';
    }
    return 'Unavailable';
  }

  Widget _buildStatusBanner() {
    Color bgColor;
    String statusText;
    
    switch (_trackingStatus) {
      case "LIVE":
        bgColor = Colors.green;
        statusText = "LIVE: Your bus is on the way";
        break;
      case "STALE":
        bgColor = Colors.orange;
        statusText = "Location may be outdated";
        break;
      case "UNAVAILABLE":
        bgColor = Colors.redAccent;
        statusText = "Live location unavailable";
        break;
      case "NO_ACTIVE_TRIP":
        bgColor = Colors.blueGrey;
        statusText = "Bus is not currently on an active trip.";
        break;
      default:
        bgColor = Colors.grey;
        statusText = "No bus assigned";
    }

    return Container(
      width: double.infinity,
      color: bgColor,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Text(
        statusText,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        textAlign: TextAlign.center,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6))),
      );
    }

    if (_error != null && _trackingStatus == "LOADING") {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        body: Center(child: Text(_error!, style: const TextStyle(color: Colors.redAccent))),
      );
    }

    final hasLocation = _location != null;
    final latLng = hasLocation ? LatLng(_location!['latitude'], _location!['longitude']) : null;
    
    // Time logic
    String lastUpdated = "";
    if (hasLocation && _location!['recorded_at'] != null) {
      try {
        final recorded = DateTime.parse(_location!['recorded_at']).toLocal();
        final diff = DateTime.now().difference(recorded).inSeconds;
        lastUpdated = diff < 60 ? 'Updated $diff seconds ago' : 'Updated ${diff ~/ 60} minutes ago';
      } catch (e) {
        lastUpdated = "Updated recently";
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: Column(
        children: [
          _buildStatusBanner(),
          if (_route != null)
            Container(
              padding: const EdgeInsets.all(12),
              color: const Color(0xFF1E293B),
              child: Row(
                children: [
                  const Icon(Icons.route, color: Color(0xFF3B82F6)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _route!['name'] ?? 'Unknown Route',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                        ),

                        if (_direction != null)
                          Text(
                            _direction!,
                            style: const TextStyle(color: Colors.white70, fontSize: 12),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          if (_stopIntelligence != null)
            Container(
              padding: const EdgeInsets.all(12),
              color: const Color(0xFF0F172A),
              child: Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: _stopIntelligence!['status'] == 'AT_STOP' ? Colors.green : Colors.transparent),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _stopIntelligence!['status'] == 'AT_STOP' ? 'CURRENT STOP' : 'CURRENT',
                            style: const TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _stopIntelligence!['status'] == 'BETWEEN_STOPS' ? 'Between Stops' : (_stopIntelligence!['current_stop']?['name'] ?? 'Not reached'),
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.arrow_forward, color: Colors.white38, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'NEXT STOP',
                            style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _stopIntelligence!['next_stop']?['name'] ?? 'None',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          if (_eta != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              color: const Color(0xFF0F172A),
              child: Row(
                children: [
                  const Icon(Icons.timer, color: Colors.orangeAccent),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'ESTIMATED ARRIVAL',
                        style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        _getEtaText(),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                    ],
                  ),
                ],
              ),
            ),

          Expanded(
            child: Stack(
              children: [
                if (hasLocation)
                  FlutterMap(
                    mapController: _mapController,
                    options: MapOptions(
                      initialCenter: latLng!,
                      initialZoom: 16.0,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.example.smartbus',
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: latLng,
                            width: 80,
                            height: 80,
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.blueAccent,
                                    borderRadius: BorderRadius.circular(4),
                                    boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
                                  ),
                                  child: Text(
                                    _bus?['bus_number'] ?? 'BUS',
                                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                const Icon(Icons.directions_bus, color: Colors.blueAccent, size: 30),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  )
                else
                  Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.location_off, size: 80, color: Colors.white24),
                        const SizedBox(height: 16),
                        Text(
                          _bus == null ? 'No Bus Assigned' : 'Location Not Available',
                          style: const TextStyle(color: Colors.white54, fontSize: 18),
                        ),
                      ],
                    ),
                  ),
                  
                if (hasLocation && lastUpdated.isNotEmpty)
                  Positioned(
                    bottom: 16,
                    left: 16,
                    right: 16,
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B).withValues(alpha: 0.9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline, color: Colors.white54, size: 20),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              '$_trackingStatus - $lastUpdated',
                              style: const TextStyle(color: Colors.white, fontSize: 14),
                            ),
                          ),
                          FloatingActionButton.small(
                            backgroundColor: const Color(0xFF3B82F6),
                            child: const Icon(Icons.my_location),
                            onPressed: () {
                              _mapController.move(latLng!, 16.0);
                            },
                          ),
                        ],
                      ),
                    ),
                  )
              ],
            ),
          ),
        ],
      ),
    );
  }
}
