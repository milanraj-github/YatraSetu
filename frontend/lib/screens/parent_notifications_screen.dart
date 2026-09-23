import 'package:flutter/material.dart';

import '../services/api_service.dart';

class ParentNotificationsScreen extends StatefulWidget {
  const ParentNotificationsScreen({super.key});

  @override
  State<ParentNotificationsScreen> createState() => _ParentNotificationsScreenState();
}

class _ParentNotificationsScreenState extends State<ParentNotificationsScreen> {
  List<dynamic> _notifications = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
  }

  Future<void> _fetchNotifications() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final res = await ApiService.getNotifications();
      if (mounted) {
        if (res['success'] == true) {
          setState(() {
            _notifications = res['data'] ?? [];
            _isLoading = false;
          });
        } else {
          setState(() {
            _error = res['error'] ?? "Failed to load notifications.";
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

  Future<void> _markRead(int id) async {
    try {
      await ApiService.markNotificationRead(id);
      setState(() {
        final index = _notifications.indexWhere((n) => n['id'] == id);
        if (index != -1) {
          _notifications[index]['status'] = 'READ';
        }
      });
    } catch (e) {
      // Ignore
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

    if (_error != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error!, style: const TextStyle(color: Colors.redAccent)),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _fetchNotifications,
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF3B82F6)),
                child: const Text("Retry"),
              )
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Notifications', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: _notifications.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_off, size: 80, color: Colors.white24),
                  SizedBox(height: 24),
                  Text('NOTIFICATIONS', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                  SizedBox(height: 16),
                  Text('No notifications yet.', style: TextStyle(color: Colors.white54, fontSize: 16)),
                ],
              ),
            )
          : RefreshIndicator(
              onRefresh: _fetchNotifications,
              child: ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _notifications.length,
                itemBuilder: (context, index) {
                  final notif = _notifications[index];
                  final isUnread = notif['status'] != 'READ';
                  final createdAt = DateTime.tryParse(notif['created_at']) ?? DateTime.now();
                  
                  final diff = DateTime.now().difference(createdAt);
                  String timeText = '';
                  if (diff.inDays > 1) {
                    timeText = '${diff.inDays} days ago';
                  } else if (diff.inDays == 1) {
                    timeText = 'Yesterday';
                  } else if (diff.inHours > 0) {
                    timeText = '${diff.inHours} hours ago';
                  } else if (diff.inMinutes > 0) {
                    timeText = '${diff.inMinutes} minutes ago';
                  } else {
                    timeText = 'Just now';
                  }


                  return Card(
                    color: isUnread ? const Color(0xFF1E293B) : const Color(0xFF1E293B).withValues(alpha: 0.5),
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: BorderSide(color: isUnread ? const Color(0xFF3B82F6) : Colors.transparent, width: 1),
                    ),
                    child: ListTile(
                      contentPadding: const EdgeInsets.all(16),
                      title: Text(
                        notif['title'] ?? '',
                        style: TextStyle(
                          color: isUnread ? Colors.white : Colors.white70,
                          fontWeight: isUnread ? FontWeight.bold : FontWeight.normal,
                          fontSize: 16,
                        ),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 8),
                          Text(
                            notif['message'] ?? '',
                            style: TextStyle(color: isUnread ? Colors.white70 : Colors.white54, fontSize: 14),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            timeText,
                            style: const TextStyle(color: Colors.blueGrey, fontSize: 12),
                          ),
                        ],
                      ),
                      onTap: () {
                        if (isUnread) _markRead(notif['id']);
                      },
                    ),
                  );
                },
              ),
            ),
    );
  }
}
