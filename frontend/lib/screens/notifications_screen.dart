import 'package:flutter/material.dart';
import '../services/api_service.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  bool _isLoading = true;
  List<dynamic> _notifications = [];

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
  }

  Future<void> _fetchNotifications() async {
    setState(() => _isLoading = true);
    final res = await ApiService.getNotifications();
    if (res['success'] == true && mounted) {
      setState(() {
        _notifications = res['data'] ?? [];
        _isLoading = false;
      });
    } else if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _markAsRead(int id, int index) async {
    if (_notifications[index]['status'] == 'READ') return;
    
    // Optimistic update
    setState(() {
      _notifications[index]['status'] = 'READ';
    });
    
    await ApiService.markNotificationRead(id);
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'CRITICAL': return Colors.red;
      case 'HIGH': return Colors.orange;
      case 'LOW': return Colors.grey;
      default: return Colors.blue;
    }
  }

  IconData _getIconForType(String type) {
    if (type.contains('SOS') || type.contains('ESCALATED')) return Icons.emergency;
    if (type.contains('DEVIATION')) return Icons.route;
    if (type.contains('TRIP')) return Icons.directions_bus;
    return Icons.notifications;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      backgroundColor: const Color(0xFF0F172A),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
        : _notifications.isEmpty
          ? const Center(child: Text("No notifications", style: TextStyle(color: Colors.white70)))
          : ListView.builder(
              itemCount: _notifications.length,
              itemBuilder: (context, index) {
                final notif = _notifications[index];
                final isUnread = notif['status'] != 'READ';
                
                return InkWell(
                  onTap: () => _markAsRead(notif['id'], index),
                  child: Container(
                    color: isUnread ? const Color(0xFF1E293B) : Colors.transparent,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        CircleAvatar(
                          backgroundColor: _getPriorityColor(notif['priority']).withValues(alpha: 0.2),
                          child: Icon(_getIconForType(notif['event_type']), color: _getPriorityColor(notif['priority']), size: 20),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(notif['title'], style: TextStyle(color: Colors.white, fontWeight: isUnread ? FontWeight.bold : FontWeight.normal, fontSize: 16)),
                              const SizedBox(height: 4),
                              Text(notif['message'], style: const TextStyle(color: Colors.white70, fontSize: 14)),
                            ],
                          ),
                        ),
                        if (isUnread)
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Colors.blue,
                              shape: BoxShape.circle,
                            ),
                          )
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
