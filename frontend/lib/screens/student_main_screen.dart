import 'package:flutter/material.dart';
import '../services/firebase_auth_service.dart';
import '../services/api_service.dart';
import '../services/notification_service.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'auth_screen.dart';
import 'student_dashboard_screen.dart';
import 'student_profile_screen.dart';
import 'student_live_bus_screen.dart';
import 'student_notifications_screen.dart';
import 'student_trip_history_screen.dart';

class StudentMainScreen extends StatefulWidget {
  const StudentMainScreen({super.key});

  @override
  State<StudentMainScreen> createState() => _StudentMainScreenState();
}

class _StudentMainScreenState extends State<StudentMainScreen> {
  final FirebaseAuthService _authService = FirebaseAuthService();
  int _currentIndex = 0;
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic>? _student;
  Map<String, dynamic>? _busData;
  int _unreadCount = 0;


  @override
  void initState() {
    super.initState();
    _fetchDashboardData();
    NotificationService().initialize();
    NotificationService().onMessageReceived = (message) {
       _fetchDashboardData();
    };
    
    _setupInteractedMessage();
  }

  Future<void> _setupInteractedMessage() async {
    RemoteMessage? initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    if (initialMessage != null) {
      _handleMessage(initialMessage);
    }
    FirebaseMessaging.onMessageOpenedApp.listen(_handleMessage);
  }

  void _handleMessage(RemoteMessage message) {
    if (message.data['type'] == 'BUS_TRIP_STARTED' || 
        message.data['type'] == 'BUS_TRIP_ENDED' || 
        message.data['type'] == 'ROUTE_DEVIATION') {
      setState(() {
        _currentIndex = 1; // Live Bus
      });
    } else {
      setState(() {
        _currentIndex = 2; // Notifications
      });
    }
  }


  Future<void> _fetchDashboardData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final userRes = await ApiService.syncUser();
      if (!mounted) return;
      
      if (userRes['status'] == 401 || userRes['status'] == 403) {
         _handleLogout();
         return;
      }
      
      if (userRes['success'] == true && userRes['data'] != null && userRes['data']['user'] != null) {
        _student = userRes['data']['user'];
        if (_student!['role'] != 'STUDENT') {
          setState(() { _error = "You are not authorized to access Student information."; _isLoading = false; });
          return;
        }
      }
      
      final busRes = await ApiService.getStudentBus();
      if (mounted && busRes['success'] == true) {
        if (busRes['data'] != null && busRes['data']['assigned'] == true) {
           _busData = busRes['data']['bus'];
        } else {
           _busData = null;
        }
      }
      
      try {
        final notifRes = await ApiService.getNotificationsUnreadCount();
        if (mounted && notifRes['success'] == true) {
          _unreadCount = notifRes['data']['unread_count'] ?? 0;
        }
      } catch (e) {
        // Ignore
      }

      
      setState(() {
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = "Unable to connect to SMARTBUS.";
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleLogout() async {
    await NotificationService().deactivate();
    await _authService.signOut();

    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Color(0xFF3B82F6)),
            SizedBox(height: 16),
            Text("Loading your profile...", style: TextStyle(color: Colors.white70)),
          ],
        )),
      );
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text("Unable to load your profile.", style: const TextStyle(color: Colors.white, fontSize: 18)),
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.redAccent, fontSize: 14)),
              const SizedBox(height: 24),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF3B82F6)),
                onPressed: _fetchDashboardData, 
                child: const Text("Retry", style: TextStyle(color: Colors.white))
              ),
              const SizedBox(height: 16),
              TextButton(onPressed: _handleLogout, child: const Text("Logout", style: TextStyle(color: Colors.redAccent))),
            ],
          ),
        ),
      );
    }

    final List<Widget> pages = [
      StudentDashboardScreen(student: _student, bus: _busData, onRefresh: _fetchDashboardData),
      const StudentLiveBusScreen(),
      const StudentNotificationsScreen(),
      const StudentTripHistoryScreen(),
      StudentProfileScreen(studentData: _student!),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('SMARTBUS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E293B),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white),
            tooltip: 'Logout',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: pages[_currentIndex],
      bottomNavigationBar: Theme(
        data: Theme.of(context).copyWith(
          canvasColor: const Color(0xFF1E293B),
        ),
        child: BottomNavigationBar(
          backgroundColor: const Color(0xFF1E293B),
          currentIndex: _currentIndex,
          selectedItemColor: const Color(0xFF3B82F6),
          unselectedItemColor: Colors.white54,
          type: BottomNavigationBarType.fixed,
          onTap: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          items: [
            const BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
            const BottomNavigationBarItem(icon: Icon(Icons.location_on), label: 'Live Bus'),
            BottomNavigationBarItem(
              icon: Badge(
                isLabelVisible: _unreadCount > 0,
                label: Text(_unreadCount.toString()),
                child: const Icon(Icons.notifications),
              ),
              label: 'Alerts',
            ),
            const BottomNavigationBarItem(icon: Icon(Icons.history), label: 'Trips'),
            const BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
          ],
        ),
      ),
    );
  }
}
