import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'trip_details_screen.dart';

class TripHistoryScreen extends StatefulWidget {
  const TripHistoryScreen({super.key});

  @override
  State<TripHistoryScreen> createState() => _TripHistoryScreenState();
}

class _TripHistoryScreenState extends State<TripHistoryScreen> {
  bool _isLoading = true;
  List<dynamic> _trips = [];

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() => _isLoading = true);
    final res = await ApiService.getTripHistory(limit: 50);
    if (res['success'] == true && mounted) {
      setState(() {
        _trips = res['data'] ?? [];
        _isLoading = false;
      });
    } else if (mounted) {
      setState(() => _isLoading = false);
    }
  }
  
  String _formatTime(String? timeStr) {
    if (timeStr == null) return 'N/A';
    final parsed = DateTime.tryParse(timeStr);
    if (parsed != null) {
      return "${parsed.day.toString().padLeft(2, '0')}/${parsed.month.toString().padLeft(2, '0')}/${parsed.year} ${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}";
    }
    return timeStr;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Past Trips'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      backgroundColor: const Color(0xFF0F172A),
      body: _isLoading
        ? const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
        : _trips.isEmpty
          ? const Center(child: Text("No past trips found.", style: TextStyle(color: Colors.white70)))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _trips.length,
              itemBuilder: (context, index) {
                final trip = _trips[index];
                final route = trip['route'];
                final session = trip['session'];
                
                return Card(
                  color: const Color(0xFF1E293B),
                  margin: const EdgeInsets.only(bottom: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: const CircleAvatar(
                      backgroundColor: Color(0xFF334155),
                      child: Icon(Icons.directions_bus, color: Colors.white),
                    ),
                    title: Text(route?['name'] ?? 'Unknown Route', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text('Ended: ${_formatTime(session?['ended_at'])}', style: const TextStyle(color: Colors.white54, fontSize: 12)),
                        const SizedBox(height: 2),
                        Text('Direction: ${session?['direction'] ?? 'UNKNOWN'}', style: const TextStyle(color: Colors.white54, fontSize: 12)),
                      ],
                    ),
                    trailing: const Icon(Icons.chevron_right, color: Colors.white54),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => TripDetailsScreen(trip: trip)),
                      );
                    },
                  ),
                );
              },
            ),
    );
  }
}
