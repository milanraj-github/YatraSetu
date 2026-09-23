import 'package:flutter/material.dart';
import '../services/api_service.dart';

/// StudentTripHistoryScreen
///
/// Displays historical bus trips that are relevant to the authenticated student,
/// as determined by their S3 bus assignment history. Calls the real backend
/// endpoint GET /api/v1/students/me/trips/history — read-only.
class StudentTripHistoryScreen extends StatefulWidget {
  const StudentTripHistoryScreen({super.key});

  @override
  State<StudentTripHistoryScreen> createState() => _StudentTripHistoryScreenState();
}

class _StudentTripHistoryScreenState extends State<StudentTripHistoryScreen> {
  List<dynamic> _trips = [];
  bool _isLoading = true;
  String? _error;
  int _page = 1;
  static const int _pageSize = 20;
  int _total = 0;
  bool _isLoadingMore = false;

  @override
  void initState() {
    super.initState();
    _fetchHistory(reset: true);
  }

  Future<void> _fetchHistory({bool reset = false}) async {
    if (_isLoading || _isLoadingMore) return;
    setState(() {
      if (reset) {
        _isLoading = true;
        _error = null;
        _page = 1;
        _trips = [];
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final res = await ApiService.getStudentTripHistory(page: _page, pageSize: _pageSize);
      if (!mounted) return;

      if (res['success'] == true) {
        final data = res['data'];
        final List<dynamic> items = data['items'] ?? [];
        setState(() {
          if (reset) {
            _trips = items;
          } else {
            _trips.addAll(items);
          }
          _total = data['total'] ?? 0;
          _isLoading = false;
          _isLoadingMore = false;
        });
      } else {
        setState(() {
          _error = res['error'] ?? 'Failed to load trip history.';
          _isLoading = false;
          _isLoadingMore = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Network error. Please try again.';
          _isLoading = false;
          _isLoadingMore = false;
        });
      }
    }
  }

  Future<void> _refresh() async {
    _isLoading = false;
    _isLoadingMore = false;
    await _fetchHistory(reset: true);
  }

  void _loadMore() {
    if (_trips.length < _total) {
      _page++;
      _fetchHistory();
    }
  }

  String _formatDateStr(String? dateStr) {
    if (dateStr == null) return 'Unknown date';
    try {
      final d = DateTime.parse(dateStr);
      return '${d.day.toString().padLeft(2, '0')} ${_monthName(d.month)} ${d.year}';
    } catch (_) {
      return dateStr;
    }
  }

  String _monthName(int m) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[(m - 1).clamp(0, 11)];
  }

  String _formatTimestamp(String? ts) {
    if (ts == null) return 'N/A';
    try {
      final d = DateTime.parse(ts).toLocal();
      final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
      final m = d.minute.toString().padLeft(2, '0');
      final period = d.hour < 12 ? 'AM' : 'PM';
      return '$h:$m $period';
    } catch (_) {
      return ts;
    }
  }

  String _formatDuration(int? secs) {
    if (secs == null) return 'Unavailable';
    if (secs < 60) return '$secs sec';
    final mins = secs ~/ 60;
    if (mins < 60) return '$mins min';
    final hours = mins ~/ 60;
    final rem = mins % 60;
    return rem > 0 ? '${hours}h ${rem}m' : '${hours}h';
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return Colors.greenAccent;
      case 'CANCELLED': return Colors.redAccent;
      case 'ACTIVE': return const Color(0xFF3B82F6);
      default: return Colors.white54;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6))),
      );
    }

    if (_error != null && _trips.isEmpty) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, color: Colors.redAccent, size: 60),
                const SizedBox(height: 16),
                Text(_error!, textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white70, fontSize: 16)),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF3B82F6)),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Trip History',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
            if (_total > 0)
              Text('$_total trip${_total == 1 ? '' : 's'} found',
                  style: const TextStyle(color: Colors.white54, fontSize: 12)),
          ],
        ),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: _trips.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.history, size: 80, color: Colors.white24),
                  SizedBox(height: 24),
                  Text('TRIP HISTORY',
                      style: TextStyle(color: Colors.white, fontSize: 20,
                          fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                  SizedBox(height: 16),
                  Text('No trip history yet.',
                      style: TextStyle(color: Colors.white54, fontSize: 16)),
                  SizedBox(height: 8),
                  Text('Completed trips will appear here.',
                      style: TextStyle(color: Colors.white38, fontSize: 13)),
                ],
              ),
            )
          : RefreshIndicator(
              onRefresh: _refresh,
              color: const Color(0xFF3B82F6),
              child: NotificationListener<ScrollNotification>(
                onNotification: (scroll) {
                  if (scroll is ScrollEndNotification &&
                      scroll.metrics.pixels >= scroll.metrics.maxScrollExtent - 100) {
                    _loadMore();
                  }
                  return false;
                },
                child: ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _trips.length + (_trips.length < _total ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == _trips.length) {
                      return const Padding(
                        padding: EdgeInsets.all(16),
                        child: Center(
                          child: CircularProgressIndicator(color: Color(0xFF3B82F6)),
                        ),
                      );
                    }

                    final trip = _trips[index];
                    return _TripCard(
                      trip: trip,
                      formatDate: _formatDateStr,
                      formatTime: _formatTimestamp,
                      formatDuration: _formatDuration,
                      statusColor: _statusColor,
                    );
                  },
                ),
              ),
            ),
    );
  }
}


class _TripCard extends StatelessWidget {
  final Map<String, dynamic> trip;
  final String Function(String?) formatDate;
  final String Function(String?) formatTime;
  final String Function(int?) formatDuration;
  final Color Function(String) statusColor;

  const _TripCard({
    required this.trip,
    required this.formatDate,
    required this.formatTime,
    required this.formatDuration,
    required this.statusColor,
  });

  @override
  Widget build(BuildContext context) {
    final bus = trip['bus'];
    final route = trip['route'];
    final direction = trip['direction'] as String? ?? 'UNKNOWN';
    final statusStr = trip['status'] as String? ?? 'UNKNOWN';
    final startedAt = trip['started_at'] as String?;
    final endedAt = trip['ended_at'] as String?;
    final durationSecs = trip['duration_seconds'] as int?;
    final dateStr = trip['date'] as String?;

    return Card(
      color: const Color(0xFF1E293B),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => StudentTripDetailScreen(trip: trip),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row: date + status badge
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(formatDate(dateStr),
                      style: const TextStyle(color: Colors.white54, fontSize: 12,
                          fontWeight: FontWeight.w600)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusColor(statusStr).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: statusColor(statusStr).withValues(alpha: 0.5)),
                    ),
                    child: Text(
                      statusStr[0] + statusStr.substring(1).toLowerCase(),
                      style: TextStyle(color: statusColor(statusStr), fontSize: 11,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Bus + Route
              Row(
                children: [
                  const Icon(Icons.directions_bus, color: Color(0xFF3B82F6), size: 20),
                  const SizedBox(width: 8),
                  Text(bus?['bus_number'] ?? 'Unknown Bus',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold,
                          fontSize: 16)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(route?['name'] ?? 'Unknown Route',
                        style: const TextStyle(color: Colors.white70, fontSize: 14),
                        overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Direction + Time range
              Row(
                children: [
                  Icon(
                    direction == 'MORNING' ? Icons.wb_sunny : Icons.nightlight_round,
                    color: direction == 'MORNING' ? Colors.orangeAccent : Colors.blueAccent,
                    size: 14,
                  ),
                  const SizedBox(width: 4),
                  Text(direction[0] + direction.substring(1).toLowerCase(),
                      style: const TextStyle(color: Colors.white54, fontSize: 12)),
                  const SizedBox(width: 12),
                  const Icon(Icons.access_time, color: Colors.white38, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    startedAt != null
                        ? '${formatTime(startedAt)} – ${formatTime(endedAt)}'
                        : 'Times unavailable',
                    style: const TextStyle(color: Colors.white54, fontSize: 12),
                  ),
                ],
              ),

              if (durationSecs != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(Icons.timer_outlined, color: Colors.white38, size: 14),
                    const SizedBox(width: 4),
                    Text(formatDuration(durationSecs),
                        style: const TextStyle(color: Colors.white54, fontSize: 12)),
                  ],
                ),
              ],

              const SizedBox(height: 8),
              const Align(
                alignment: Alignment.centerRight,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('View details', style: TextStyle(color: Color(0xFF3B82F6), fontSize: 12)),
                    SizedBox(width: 2),
                    Icon(Icons.chevron_right, color: Color(0xFF3B82F6), size: 16),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


/// Read-only trip detail screen for students.
class StudentTripDetailScreen extends StatelessWidget {
  final Map<String, dynamic> trip;

  const StudentTripDetailScreen({super.key, required this.trip});

  String _formatTimestamp(String? ts) {
    if (ts == null) return 'N/A';
    try {
      final d = DateTime.parse(ts).toLocal();
      final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
      final m = d.minute.toString().padLeft(2, '0');
      final period = d.hour < 12 ? 'AM' : 'PM';
      return '$h:$m $period';
    } catch (_) {
      return ts;
    }
  }

  String _formatDateStr(String? dateStr) {
    if (dateStr == null) return 'Unknown date';
    try {
      final d = DateTime.parse(dateStr);
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return '${d.day.toString().padLeft(2,'0')} ${months[d.month - 1]} ${d.year}';
    } catch (_) {
      return dateStr;
    }
  }

  String _formatDuration(int? secs) {
    if (secs == null) return 'Unavailable';
    final mins = secs ~/ 60;
    if (mins < 60) return '$mins min';
    final hours = mins ~/ 60;
    final rem = mins % 60;
    return rem > 0 ? '${hours}h ${rem}m' : '${hours}h';
  }

  @override
  Widget build(BuildContext context) {
    final bus = trip['bus'];
    final route = trip['route'];
    final direction = (trip['direction'] as String? ?? 'UNKNOWN');
    final statusStr = (trip['status'] as String? ?? 'UNKNOWN');
    final startedAt = trip['started_at'] as String?;
    final endedAt = trip['ended_at'] as String?;
    final durationSecs = trip['duration_seconds'] as int?;
    final dateStr = trip['date'] as String?;

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Trip Details',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _statusBgColor(statusStr),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  Icon(_statusIcon(statusStr), color: Colors.white, size: 20),
                  const SizedBox(width: 10),
                  Text(
                    '${statusStr[0]}${statusStr.substring(1).toLowerCase()}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold,
                        fontSize: 16),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Details card
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                children: [
                  _DetailRow(label: 'Date', value: _formatDateStr(dateStr), icon: Icons.calendar_today),
                  _DetailRow(label: 'Bus', value: bus?['bus_number'] ?? 'Unknown', icon: Icons.directions_bus),
                  _DetailRow(label: 'Route', value: route?['name'] ?? 'Unknown', icon: Icons.route),
                  _DetailRow(
                    label: 'Direction',
                    value: '${direction[0]}${direction.substring(1).toLowerCase()}',
                    icon: Icons.swap_horiz,
                  ),
                  _DetailRow(
                    label: 'Started',
                    value: _formatTimestamp(startedAt),
                    icon: Icons.play_circle_outline,
                  ),
                  _DetailRow(
                    label: 'Ended',
                    value: endedAt != null ? _formatTimestamp(endedAt) : 'N/A',
                    icon: Icons.stop_circle_outlined,
                    isLast: durationSecs == null,
                  ),
                  if (durationSecs != null)
                    _DetailRow(
                      label: 'Duration',
                      value: _formatDuration(durationSecs),
                      icon: Icons.timer_outlined,
                      isLast: true,
                    ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Route code
            if (route?['code'] != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.confirmation_number, color: Colors.white54, size: 16),
                    const SizedBox(width: 8),
                    Text('Route code: ${route!['code']}',
                        style: const TextStyle(color: Colors.white54, fontSize: 13)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Color _statusBgColor(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return const Color(0xFF166534);
      case 'CANCELLED': return const Color(0xFF7F1D1D);
      default: return const Color(0xFF1E3A5F);
    }
  }

  IconData _statusIcon(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return Icons.check_circle;
      case 'CANCELLED': return Icons.cancel;
      default: return Icons.info;
    }
  }
}


class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final bool isLast;

  const _DetailRow({
    required this.label,
    required this.value,
    required this.icon,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Icon(icon, color: Colors.white54, size: 18),
              const SizedBox(width: 12),
              Text(label, style: const TextStyle(color: Colors.white54, fontSize: 14)),
              const Spacer(),
              Flexible(
                child: Text(value,
                    style: const TextStyle(color: Colors.white, fontSize: 14,
                        fontWeight: FontWeight.w600),
                    textAlign: TextAlign.end),
              ),
            ],
          ),
        ),
        if (!isLast)
          const Divider(color: Color(0xFF334155), height: 1, indent: 16, endIndent: 16),
      ],
    );
  }
}
