import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ParentTripHistoryScreen extends StatefulWidget {
  final int studentId;
  final String studentName;

  const ParentTripHistoryScreen({super.key, required this.studentId, required this.studentName});

  @override
  State<ParentTripHistoryScreen> createState() => _ParentTripHistoryScreenState();
}

class _ParentTripHistoryScreenState extends State<ParentTripHistoryScreen> {
  bool _isLoading = true;
  String? _error;
  List<dynamic> _trips = [];

  @override
  void initState() {
    super.initState();
    _fetchTripHistory();
  }

  Future<void> _fetchTripHistory() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final res = await ApiService.getParentStudentTripHistory(widget.studentId);
      if (mounted) {
        if (res['success'] == true) {
          setState(() {
            _trips = res['data']?['items'] ?? [];
            _isLoading = false;
          });
        } else {
          setState(() {
            _error = res['error'] ?? "Failed to load trip history.";
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
  
  String _formatTime(String? isoString) {
    if (isoString == null) return "Unknown";
    final dt = DateTime.tryParse(isoString);
    if (dt == null) return "Unknown";
    final local = dt.toLocal();
    final hours = local.hour > 12 ? local.hour - 12 : (local.hour == 0 ? 12 : local.hour);
    final ampm = local.hour >= 12 ? "PM" : "AM";
    final min = local.minute.toString().padLeft(2, '0');
    return "$hours:$min $ampm";
  }

  Widget _buildTripCard(dynamic trip) {
    final status = trip['status'];
    Color statusColor = Colors.grey;
    if (status == 'COMPLETED') statusColor = Colors.green;
    if (status == 'CANCELLED') statusColor = Colors.red;

    final busNum = trip['bus']?['bus_number'] ?? "Unknown Bus";
    final routeName = trip['route']?['name'] ?? "Unknown Route";
    final direction = trip['direction'] ?? "Unknown";
    final dateStr = trip['date'] ?? "Unknown Date";

    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: statusColor.withValues(alpha: 0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  busNum,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    status.toString(),
                    style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              "Route: $routeName",
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 4),
            Text(
              "Direction: $direction",
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 4),
            Text(
              "Date: $dateStr",
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Started", style: TextStyle(color: Colors.white38, fontSize: 12)),
                    Text(_formatTime(trip['started_at']), style: const TextStyle(color: Colors.white, fontSize: 14)),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text("Ended", style: TextStyle(color: Colors.white38, fontSize: 12)),
                    Text(_formatTime(trip['ended_at']), style: const TextStyle(color: Colors.white, fontSize: 14)),
                  ],
                ),
              ],
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
        title: Text('${widget.studentName} History', style: const TextStyle(color: Colors.white, fontSize: 18)),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.blue))
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : _trips.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.history, color: Colors.blueGrey, size: 64),
                          SizedBox(height: 16),
                          Text('No travel history yet.', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _fetchTripHistory,
                      child: ListView.builder(
                        itemCount: _trips.length,
                        itemBuilder: (context, index) {
                          return _buildTripCard(_trips[index]);
                        },
                      ),
                    ),
    );
  }
}
