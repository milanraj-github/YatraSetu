import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ParentSafetyScreen extends StatefulWidget {
  const ParentSafetyScreen({super.key});

  @override
  State<ParentSafetyScreen> createState() => _ParentSafetyScreenState();
}

class _ParentSafetyScreenState extends State<ParentSafetyScreen> {
  bool _isLoading = true;
  String? _error;
  List<dynamic> _activeEvents = [];
  List<dynamic> _recentEvents = [];

  @override
  void initState() {
    super.initState();
    _fetchSafetyEvents();
  }

  Future<void> _fetchSafetyEvents() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final res = await ApiService.getMySafetyEvents();
      if (mounted) {
        if (res['success'] == true) {
          setState(() {
            _activeEvents = res['data']?['active_events'] ?? [];
            _recentEvents = res['data']?['recent_events'] ?? [];
            _isLoading = false;
          });
        } else {
          setState(() {
            _error = res['error'] ?? "Failed to load safety events.";
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = "Network error. Please try again.";
          _isLoading = false;
        });
      }
    }
  }

  Widget _buildEventCard(dynamic event, bool isActive) {
    Color statusColor = isActive ? Colors.orange : Colors.grey;
    if (event['severity'] == 'CRITICAL' && isActive) {
      statusColor = Colors.red;
    } else if (event['status'] == 'DRIVER_CONFIRMED_SAFE') {
      statusColor = Colors.green;
    }

    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: statusColor.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  event['event_category'] == 'EMERGENCY' ? Icons.warning_amber_rounded : Icons.info_outline,
                  color: statusColor,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    event['event_type'].toString().replaceAll('_', ' '),
                    style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    event['status'].toString().replaceAll('_', ' '),
                    style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              "Student: ${event['student']['full_name']}",
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
            Text(
              "Bus: ${event['bus']['bus_number']}",
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Text(
              event['description'] ?? '',
              style: const TextStyle(color: Colors.white54, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Text(
              "Detected: ${DateTime.parse(event['detected_at']).toLocal().toString().split('.')[0]}",
              style: const TextStyle(color: Colors.white38, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Safety & Emergency', style: TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _fetchSafetyEvents,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.orange))
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : (_activeEvents.isEmpty && _recentEvents.isEmpty)
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.health_and_safety, color: Colors.green, size: 64),
                          SizedBox(height: 16),
                          Text('No active safety alerts', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                          SizedBox(height: 8),
                          Text('Your linked students currently have no active safety events.', style: TextStyle(color: Colors.white54), textAlign: TextAlign.center),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _fetchSafetyEvents,
                      child: ListView(
                        children: [
                          if (_activeEvents.isNotEmpty) ...[
                            const Padding(
                              padding: EdgeInsets.all(16),
                              child: Text('ACTIVE ALERTS', style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
                            ),
                            ..._activeEvents.map((e) => _buildEventCard(e, true)),
                          ],
                          if (_recentEvents.isNotEmpty) ...[
                            const Padding(
                              padding: EdgeInsets.all(16),
                              child: Text('RECENT EVENTS', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
                            ),
                            ..._recentEvents.map((e) => _buildEventCard(e, false)),
                          ],
                        ],
                      ),
                    ),
    );
  }
}
