import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/firebase_auth_service.dart';
import 'auth_screen.dart';
import '../services/location_service.dart';
import '../services/notification_service.dart';
import 'notifications_screen.dart';
import 'trip_history_screen.dart';
import 'driver_profile_screen.dart';

class DriverDashboardScreen extends StatefulWidget {
  const DriverDashboardScreen({super.key});

  @override
  State<DriverDashboardScreen> createState() => _DriverDashboardScreenState();
}

class _DriverDashboardScreenState extends State<DriverDashboardScreen> {
  bool _isLoading = true;
  int? _actionLoadingId;
  String? _error;
  
  Map<String, dynamic>? _assignment;
  Map<String, dynamic>? _bus;
  Map<String, dynamic>? _driver;
  List<dynamic> _schedules = [];
  
final FirebaseAuthService _authService = FirebaseAuthService();
  final LocationService _locationService = LocationService();
  
String _gpsStatus = 'Inactive';
  DateTime? _lastGpsUpload;
  String? _gpsError;
  bool _isOnline = true;
  int _queuedCount = 0;
  bool _isSyncing = false;
  Map<String, dynamic>? _stopIntelligence;
  Timer? _countdownTimer;
  bool _isConfirmingSafe = false;
  bool _isSendingSOS = false;
  int _unreadCount = 0;

@override
  void initState() {
    super.initState();
    _locationService.onStatusChanged = (status, lastUpload, error, isOnline, queuedCount, isSyncing, stopIntelligence) {
      if (mounted) {
        setState(() {
          _gpsStatus = status;
          _lastGpsUpload = lastUpload;
          _gpsError = error;
          _isOnline = isOnline;
          _queuedCount = queuedCount;
          _isSyncing = isSyncing;
          
          final previousAlert = _stopIntelligence?['accident_alert_id'];
          _stopIntelligence = stopIntelligence;
          
          if (_stopIntelligence?['accident_alert_id'] != null && previousAlert == null) {
            _startCountdownTimer();
          } else if (_stopIntelligence?['accident_alert_id'] == null) {
            _stopCountdownTimer();
          }
        });
      }
    };
    _fetchDashboardData();
    _initNotifications();
  }
  
  Future<void> _initNotifications() async {
    final notifService = NotificationService();
    await notifService.initialize();
    notifService.onMessageReceived = (message) {
      if (mounted) {
        _fetchUnreadCount();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(message.notification?.title ?? "New Notification"),
          backgroundColor: Colors.blue.shade800,
        ));
      }
    };
    _fetchUnreadCount();
  }

  Future<void> _fetchUnreadCount() async {
    final res = await ApiService.getUnreadNotificationCount();
    if (res['success'] == true && mounted) {
      setState(() {
        _unreadCount = res['data']['unread_count'] ?? 0;
      });
    }
  }


  void _startCountdownTimer() {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) setState(() {});
    });
  }
  
  void _stopCountdownTimer() {
    _countdownTimer?.cancel();
    _countdownTimer = null;
  }

  Future<void> _fetchDashboardData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // 1. Sync User Profile
      final userRes = await ApiService.syncUser();
      if (!mounted) return;
      
      if (userRes['status'] == 401 || userRes['status'] == 403) {
         _handleAuthError(userRes['error'] ?? 'Authentication failed');
         return;
      }
      
      if (userRes['success'] == true && userRes['data'] != null && userRes['data']['user'] != null) {
        _driver = userRes['data']['user'];
        if (_driver!['role'] != 'DRIVER') {
          setState(() { _error = "You are not authorized to access Driver information."; _isLoading = false; });
          return;
        }
        if (_driver!['status'] != 'ACTIVE') {
          setState(() { _error = "Your account is inactive. Please contact the administrator."; _isLoading = false; });
          return;
        }
      }

      // 2. Get Bus Assignment
      final res = await ApiService.getMyAssignment();
      if (!mounted) return;

      if (res['status'] == 401) {
        _handleAuthError(res['error']);
        return;
      } else if (res['status'] == 403) {
        setState(() { _error = res['error']; _isLoading = false; });
        return;
      } else if (res['status'] == 404) {
        setState(() {
          _assignment = null;
          _bus = null;
          _schedules = [];
          _isLoading = false;
        });
        return;
      }

      if (res['success'] == true && res['data'] != null && res['data']['assignment'] != null) {
        _assignment = res['data']['assignment'];
        _bus = res['data']['bus'];
      } else {
        _assignment = null;
        _bus = null;
      }

      // 3. Get Today's Schedules if we have a bus
      if (_bus != null) {
        final schedRes = await ApiService.getTodaySchedules();
        if (mounted && schedRes['success'] == true && schedRes['data'] != null) {
          _schedules = schedRes['data'];
        } else {
          _schedules = [];
        }
      }

if (mounted) {
        setState(() {
          _isLoading = false;
        });
        
        // Manage GPS Lifecycle
        bool hasActiveTrip = _schedules.any((s) => (s['session']?['status']?.toString().toUpperCase() ?? '') == 'ACTIVE');
        if (hasActiveTrip && !_locationService.isTracking) {
           _locationService.startTracking();
        } else if (!hasActiveTrip && _locationService.isTracking) {
           _locationService.stopTracking();
        }
      }

    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Unable to connect to SMARTBUS. Check your internet connection.';
        _isLoading = false;
      });
    }
  }

  void _handleAuthError(String? message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message ?? 'Your session has expired. Please sign in again.'), backgroundColor: Colors.red)
    );
    _handleLogout();
  }


  Future<void> _handleLogout() async {
    await NotificationService().deactivate();
    _locationService.stopTracking();
    await _authService.signOut();

    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  Future<void> _confirmAction(String title, String actionName, int sessionId, Map<String, dynamic> scheduleData, bool isStart) async {
    final routeName = scheduleData['route']?['name'] ?? 'Unknown Route';
    final departure = (scheduleData['schedule']?['start_time'] ?? '00:00').toString().substring(0, 5);
    final direction = scheduleData['schedule']?['direction'] ?? 'UNKNOWN';
    final busName = scheduleData['bus']?['bus_number'] ?? _bus?['bus_number'] ?? 'Unknown';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Bus: $busName', style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 4),
            Text('Route: $routeName', style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 4),
            Text('Direction: $direction', style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 4),
            Text('Scheduled: $departure', style: const TextStyle(color: Colors.white70)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: isStart ? const Color(0xFF10B981) : Colors.red),
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(actionName, style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      if (isStart) {
        _handleStartTrip(sessionId);
      } else {
        _handleEndTrip(sessionId);
      }
    }
  }

  Future<void> _handleStartTrip(int sessionId) async {
    setState(() {
      _actionLoadingId = sessionId;
    });

    final res = await ApiService.startTrip(sessionId);
    
    if (!mounted) return;
    
    if (res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip started successfully.'), backgroundColor: Color(0xFF10B981))
      );
      _locationService.startTracking();
      _fetchDashboardData();
    } else {
      setState(() {
        _actionLoadingId = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['error'] ?? 'Unable to start trip.'), backgroundColor: Colors.red)
      );
      if (res['status'] == 401 || res['status'] == 403) {
         _handleAuthError(res['error']);
      }
    }
  }

  Future<void> _handleEndTrip(int sessionId) async {
    setState(() {
      _actionLoadingId = sessionId;
    });

    final res = await ApiService.endTrip(sessionId);
    
    if (!mounted) return;
    
    if (res['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip completed successfully.'), backgroundColor: Color(0xFF10B981))
      );
      _locationService.stopTracking();
      _fetchDashboardData();
    } else {
      setState(() {
        _actionLoadingId = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['error'] ?? 'Unable to end trip.'), backgroundColor: Colors.red)
      );
      if (res['status'] == 401 || res['status'] == 403) {
         _handleAuthError(res['error']);
      }
    }
  }

  void _showRouteStops(Map<String, dynamic> scheduleData) {
    final route = scheduleData['route'];
    if (route == null) return;
    
    final stops = route['stops'] as List<dynamic>? ?? [];
    stops.sort((a, b) => (a['sequence_order'] ?? 0).compareTo(b['sequence_order'] ?? 0));

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.6,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return Column(
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 24),
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const Text('ROUTE STOPS', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                const SizedBox(height: 8),
                Text(route['name'] ?? 'Unknown', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
                const SizedBox(height: 24),
                
                Expanded(
                  child: stops.isEmpty
                    ? const Center(child: Text('No stops available', style: TextStyle(color: Colors.white54)))
                    : ListView.builder(
                        controller: scrollController,
                        itemCount: stops.length,
                        itemBuilder: (context, index) {
                          final stop = stops[index];
                          final sequence = stop['sequence_order']?.toString().padLeft(2, '0') ?? '00';
                          final bpName = stop['boarding_point']?['name'] ?? stop['name'] ?? 'Unknown Stop';
                          
                          return ListTile(
                            leading: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: const Color(0xFF3B82F6).withValues(alpha: 0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Text(sequence, style: const TextStyle(color: Color(0xFF3B82F6), fontWeight: FontWeight.bold)),
                            ),
                            title: Text(bpName, style: const TextStyle(color: Colors.white, fontSize: 16)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
                          );
                        },
                      ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      drawer: Drawer(
        backgroundColor: const Color(0xFF1E293B),
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: const BoxDecoration(color: Color(0xFF0F172A)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  const CircleAvatar(
                    radius: 30,
                    backgroundColor: Color(0xFF334155),
                    child: Icon(Icons.person, size: 40, color: Colors.white),
                  ),
                  const SizedBox(height: 12),
                  Text(_driver?['full_name'] ?? 'Driver', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.person, color: Colors.white),
              title: const Text('My Profile', style: TextStyle(color: Colors.white)),
              onTap: () async {
                Navigator.pop(context); // close drawer
                final shouldRefresh = await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => DriverProfileScreen(driverData: _driver!, busData: _bus)),
                );
                if (shouldRefresh == true) {
                  _fetchDashboardData();
                }
              },
            ),
            ListTile(
              leading: const Icon(Icons.history, color: Colors.white),
              title: const Text('Trip History', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.pop(context); // close drawer
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const TripHistoryScreen()),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.logout, color: Colors.redAccent),
              title: const Text('Logout', style: TextStyle(color: Colors.redAccent)),
              onTap: () {
                Navigator.pop(context); // close drawer
                _handleLogout();
              },
            ),
          ],
        ),
      ),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: const Text('SMARTBUS', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            tooltip: 'Refresh',
            onPressed: _fetchDashboardData,
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.notifications, color: Colors.white),
                onPressed: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const NotificationsScreen()),
                  );
                  _fetchUnreadCount(); // refresh on back
                },
              ),
              if (_unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 12,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                    child: Text(
                      '$_unreadCount',
                      style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white),
            tooltip: 'Logout',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _fetchDashboardData,
          color: const Color(0xFF10B981),
          backgroundColor: const Color(0xFF1E293B),
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildAccidentOverlay() {
    final alertId = _stopIntelligence?['accident_alert_id'];
    final deadlineStr = _stopIntelligence?['accident_deadline_at'];
    if (alertId == null || deadlineStr == null) return const SizedBox.shrink();
    
    final deadline = DateTime.parse(deadlineStr).toLocal();
    final remaining = deadline.difference(DateTime.now()).inSeconds;
    final status = _stopIntelligence?['accident_status'];
    
    if (remaining <= 0 || status == 'ESCALATED') {
      return Container(
        color: Colors.red.shade900,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.warning, size: 80, color: Colors.white),
              SizedBox(height: 24),
              Text('EMERGENCY ALERT SENT', style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
              SizedBox(height: 16),
              Text('The incident has been escalated\nto the SMARTBUS administration.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white70, fontSize: 16)),
            ],
          ),
        ),
      );
    }
    
    return Container(
      color: Colors.black87,
      child: Center(
        child: Container(
          margin: const EdgeInsets.all(24),
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: Colors.red.shade900,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.redAccent, width: 2),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.warning_amber_rounded, size: 64, color: Colors.white),
              const SizedBox(height: 16),
              const Text('POTENTIAL ACCIDENT DETECTED', textAlign: TextAlign.center, style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 24),
              const Text('Are you safe?\nPlease confirm within:', textAlign: TextAlign.center, style: TextStyle(color: Colors.white, fontSize: 16)),
              const SizedBox(height: 16),
              Text('$remaining seconds', style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
              const SizedBox(height: 24),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: _isConfirmingSafe ? null : () async {
                  setState(() => _isConfirmingSafe = true);
                  final res = await ApiService.confirmAccidentSafe(alertId);
                  if (mounted) {
                    setState(() => _isConfirmingSafe = false);
                    if (res['success'] == true) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("✓ I'M SAFE CONFIRMED. Emergency alert cancelled."), backgroundColor: Colors.green));
                      setState(() {
                        _stopIntelligence?['accident_alert_id'] = null;
                      });
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['error'] ?? 'Unable to confirm. Please try again.'), backgroundColor: Colors.red));
                    }
                  }
                },
                child: _isConfirmingSafe 
                  ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text("I'M SAFE", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 16),
              const Text('If you are unable to respond,\nemergency assistance may be notified.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white70, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }


  Widget _buildActiveSOSBanner() {
    final activeSosId = _stopIntelligence?['active_sos_id'];
    if (activeSosId == null) return const SizedBox.shrink();
    
    return Container(
      margin: const EdgeInsets.only(bottom: 16, top: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.shade900,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.redAccent, width: 2),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.emergency, color: Colors.white, size: 24),
              SizedBox(width: 8),
              Text('EMERGENCY ACTIVE', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          SizedBox(height: 8),
          Text('Administration has been notified.', style: TextStyle(color: Colors.white70, fontSize: 14)),
          SizedBox(height: 4),
          Text('Status: ACTIVE', style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_stopIntelligence?['accident_alert_id'] != null) {
      return Stack(
        children: [
          // Original body underneath
          _buildNormalBody(),
          // Overlay
          Positioned.fill(child: _buildAccidentOverlay()),
        ],
      );
    }
    return _buildNormalBody();
  }
  
  Widget _buildNormalBody() {
    if (_isLoading) {
      return ListView(
        padding: const EdgeInsets.all(24.0),
        children: const [
           Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(height: 100),
                CircularProgressIndicator(color: Color(0xFF10B981)),
                SizedBox(height: 16),
                Text('Loading your schedule...', style: TextStyle(color: Colors.white70)),
              ],
            ),
          )
        ],
      );
    }

    if (_error != null) {
      return ListView(
        padding: const EdgeInsets.all(24.0),
        children: [
          const SizedBox(height: 100),
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 16),
          Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 16), textAlign: TextAlign.center),
          const SizedBox(height: 24),
          Center(
            child: ElevatedButton(
              onPressed: _fetchDashboardData, 
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B), foregroundColor: Colors.white),
              child: const Text('Retry')
            ),
          )
        ],
      );
    }

    return ListView(
      padding: const EdgeInsets.all(24.0),
      children: [
        _buildActiveSOSBanner(),
        _buildHeader(),
        const SizedBox(height: 32),
        _buildBusCard(),
        const SizedBox(height: 32),
        _buildTodayAssignmentSection(),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Welcome, ${_driver?['full_name'] ?? 'Driver'}', 
          style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)
        ),
        if (_driver?['email'] != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(_driver!['email'], style: const TextStyle(color: Colors.white54, fontSize: 14)),
          ),
      ],
    );
  }

  Widget _buildBusCard() {
    if (_assignment == null || _bus == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF334155), width: 1),
        ),
        child: const Column(
          children: [
            Icon(Icons.directions_bus_outlined, color: Colors.white30, size: 64),
            SizedBox(height: 16),
            Text('NO BUS ASSIGNED', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
            SizedBox(height: 8),
            Text('Your account currently has no active bus assignment.', 
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white60, fontSize: 14)
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('YOUR BUS', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF334155), width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: Color(0xFF334155))),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.directions_bus, color: Color(0xFF10B981), size: 32),
                    const SizedBox(width: 16),
                    Text(_bus!['bus_number'] ?? 'Unknown', style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildInfoRow('Registration', _bus!['registration_number'] ?? 'N/A'),
                    const SizedBox(height: 16),
                    _buildInfoRow('Capacity', '${_bus!['capacity'] ?? 0} seats'),
                    const SizedBox(height: 16),
                    _buildInfoRow('Assignment Status', _assignment!['status'] ?? 'UNKNOWN', highlightColor: const Color(0xFF10B981)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTodayAssignmentSection() {
    if (_assignment == null || _bus == null) return const SizedBox.shrink();

    if (_schedules.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("TODAY'S SCHEDULES", style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155), width: 1),
            ),
            child: const Column(
              children: [
                Icon(Icons.event_busy, color: Colors.white30, size: 48),
                SizedBox(height: 16),
                Text('NO SCHEDULE TODAY', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                SizedBox(height: 8),
                Text('You have no scheduled bus service for today.', 
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white60, fontSize: 14)
                ),
              ],
            ),
          )
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _schedules.length == 1 ? "TODAY'S ASSIGNMENT" : "TODAY'S SCHEDULES", 
          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)
        ),
        const SizedBox(height: 12),
        ..._schedules.map((scheduleData) => _buildScheduleCard(scheduleData)),
      ],
    );
  }

  Widget _buildScheduleCard(Map<String, dynamic> scheduleData) {
    final schedule = scheduleData['schedule'];
    final session = scheduleData['session'];
    final route = scheduleData['route'];
    final bus = scheduleData['bus'];
    final sessionId = scheduleData['id'] as int?;

    if (schedule == null || session == null || route == null || sessionId == null) return const SizedBox.shrink();

    String departure = schedule['start_time'] ?? '00:00';
    if (departure.length > 5) departure = departure.substring(0, 5); // "07:35"

    final direction = schedule['direction']?.toString().toUpperCase() ?? 'UNKNOWN';
    final status = session['status']?.toString().toUpperCase() ?? 'SCHEDULED';
    final routeName = route['name'] ?? 'Unknown Route';

    String? startedAt = session['started_at'];
    if (startedAt != null) {
      final parsed = DateTime.tryParse(startedAt);
      if (parsed != null) startedAt = "${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}";
    }

    String? endedAt = session['ended_at'];
    if (endedAt != null) {
      final parsed = DateTime.tryParse(endedAt);
      if (parsed != null) endedAt = "${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}";
    }
    
    // Status color
    Color statusColor = const Color(0xFF94A3B8); // Default
    if (status == 'ACTIVE') statusColor = const Color(0xFF3B82F6);
    if (status == 'COMPLETED') statusColor = const Color(0xFF10B981);
    if (status == 'SCHEDULED') statusColor = const Color(0xFFF59E0B);
    if (status == 'CANCELLED') statusColor = Colors.red;

    final isActionLoading = _actionLoadingId == sessionId;
    final hasActiveTripOverall = _schedules.any((s) => (s['session']?['status']?.toString().toUpperCase() ?? '') == 'ACTIVE');

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF334155))),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.access_time_rounded, color: Colors.white54, size: 20),
                    const SizedBox(width: 8),
                    Text(departure, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: statusColor.withValues(alpha: 0.2)),
                  ),
                  child: Text(status, style: TextStyle(color: statusColor, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Route', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                const SizedBox(height: 4),
                Text(routeName, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                
                const SizedBox(height: 16),
                
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Direction', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                        const SizedBox(height: 4),
                        Text(direction, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Bus', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                        const SizedBox(height: 4),
                        Text(bus?['bus_number'] ?? _bus?['bus_number'] ?? 'Unknown', style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ],
                ),
                
                const SizedBox(height: 24),
                
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () => _showRouteStops(scheduleData),
                    icon: const Icon(Icons.format_list_bulleted, size: 18),
                    label: const Text('VIEW ROUTE'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Color(0xFF334155)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ),

                if (status == 'ACTIVE' && startedAt != null) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 8, bottom: 8),
                    child: Text('Started: $startedAt', style: const TextStyle(color: Color(0xFF10B981), fontSize: 14, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: _gpsStatus == 'GPS ACTIVE' ? const Color(0xFF3B82F6).withValues(alpha: 0.5) : const Color(0xFF334155)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  _gpsStatus == 'GPS ACTIVE' ? Icons.gps_fixed : Icons.gps_off, 
                                  color: _gpsStatus == 'GPS ACTIVE' ? const Color(0xFF3B82F6) : Colors.white54, 
                                  size: 20
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'GPS TRACKING', 
                                  style: TextStyle(
                                    color: _gpsStatus == 'GPS ACTIVE' ? const Color(0xFF3B82F6) : Colors.white54, 
                                    fontSize: 13, 
                                    fontWeight: FontWeight.bold, 
                                    letterSpacing: 1.2
                                  )
                                ),
                              ],
                            ),
                            Row(
                              children: [
                                Icon(
                                  _isOnline ? Icons.wifi : Icons.wifi_off,
                                  color: _isOnline ? const Color(0xFF10B981) : Colors.redAccent,
                                  size: 16,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  _isOnline ? 'ONLINE' : 'OFFLINE',
                                  style: TextStyle(
                                    color: _isOnline ? const Color(0xFF10B981) : Colors.redAccent,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: _gpsStatus == 'GPS ACTIVE' ? const Color(0xFF10B981) : Colors.orange,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(_gpsStatus, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
                          ],
                        ),
                        if (_gpsError != null) ...[
                          const SizedBox(height: 8),
                          Text(_gpsError!, style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
                        ] else if (_lastGpsUpload != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            'Last sent: ${DateTime.now().difference(_lastGpsUpload!).inSeconds} sec ago', 
                            style: const TextStyle(color: Colors.white54, fontSize: 13)
                          ),
                        ],
                        if (_queuedCount > 0) ...[
                          const SizedBox(height: 12),
                          const Divider(color: Colors.white12),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              if (_isSyncing)
                                const SizedBox(
                                  width: 14, height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.orange)
                                )
                              else
                                const Icon(Icons.cloud_upload_outlined, color: Colors.orange, size: 16),
                              const SizedBox(width: 8),
                              Text(
                                _isSyncing ? 'Syncing offline GPS...' : 'Queued locations: $_queuedCount',
                                style: const TextStyle(color: Colors.orange, fontSize: 13),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (_stopIntelligence != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.route, color: Color(0xFF10B981), size: 18),
                              const SizedBox(width: 8),
                              const Text('ROUTE INTELLIGENCE', style: TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('CURRENT STOP', style: TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 4),
                                    Text(_stopIntelligence!['current_stop']?['name'] ?? '-', style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
                                  ],
                                ),
                              ),
                              Container(width: 1, height: 30, color: Colors.white12),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('NEXT STOP', style: TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 4),
                                    Text(_stopIntelligence!['next_stop']?['name'] ?? '-', style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
                                  ],
                                ),
                              ),
                            ],
                          ),

                          if (_stopIntelligence!['deviation_status'] == 'DEVIATED' || _stopIntelligence!['deviation_status'] == 'POTENTIAL_DEVIATION') ...[
                            const SizedBox(height: 12),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.redAccent.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.redAccent.withValues(alpha: 0.5)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 24),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Text('ROUTE DEVIATION', style: TextStyle(color: Colors.redAccent, fontSize: 13, fontWeight: FontWeight.bold)),
                                        const SizedBox(height: 4),
                                        Text(
                                          _stopIntelligence!['deviation_status'] == 'POTENTIAL_DEVIATION' 
                                            ? 'Bus may be straying from route...' 
                                            : 'Bus appears to be outside the planned route. Please check the route.',
                                          style: const TextStyle(color: Colors.white70, fontSize: 12),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: const Color(0xFF1E293B),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              _stopIntelligence!['status']?.toString().replaceAll('_', ' ') ?? '-',
                              style: const TextStyle(color: Colors.orangeAccent, fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],

                if (status == 'COMPLETED')
                  Padding(
                    padding: const EdgeInsets.only(top: 8, bottom: 8),
                    child: Row(
                      children: [
                        if (startedAt != null) Text('Started: $startedAt', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                        if (startedAt != null && endedAt != null) const SizedBox(width: 16),
                        if (endedAt != null) Text('Ended: $endedAt', style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),

                // Trip Lifecycle Controls
                if (status == 'SCHEDULED' && !hasActiveTripOverall) ...[
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: isActionLoading ? null : () => _confirmAction('Start Trip?', 'START TRIP', sessionId, scheduleData, true),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      child: isActionLoading 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('START TRIP', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                    ),
                  ),
                ],

                if (status == 'ACTIVE') ...[
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: isActionLoading ? null : () => _confirmAction('End Trip?', 'END TRIP', sessionId, scheduleData, false),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      child: isActionLoading 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('END TRIP', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                    ),
                  ),
                  
                  const SizedBox(height: 24),
                  const Divider(color: Color(0xFF334155)),
                  const SizedBox(height: 12),
                  
                  if (_stopIntelligence?['active_sos_id'] == null)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isSendingSOS ? null : () => _showSOSDialog(),
                      icon: _isSendingSOS 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Icon(Icons.emergency, color: Colors.white),
                      label: Text(_isSendingSOS ? 'SENDING...' : 'SOS', style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red.shade900,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                  ),
                ],

              ],
            ),
          ),
        ],
      ),
    );
  }


  void _showSOSDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.red, size: 28),
            SizedBox(width: 8),
            Text('SEND EMERGENCY?', style: TextStyle(color: Colors.white, fontSize: 20)),
          ],
        ),
        content: const Text(
          'This will notify SMARTBUS administration about an emergency on your current trip.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red.shade900),
            onPressed: () {
              Navigator.pop(context);
              _triggerManualSOS();
            },
            child: const Text('SEND EMERGENCY', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Future<void> _triggerManualSOS() async {
    setState(() => _isSendingSOS = true);
    final res = await ApiService.sendManualSOS("Manual emergency");
    if (mounted) {
      setState(() => _isSendingSOS = false);
      if (res['success'] == true) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text("🚨 EMERGENCY SENT. Administration has been notified."),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 5),
        ));
        _fetchDashboardData(); // Refresh to pull active SOS state if needed
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res['error'] ?? 'Unable to send emergency. Check connection and try again.'),
          backgroundColor: Colors.orange,
          duration: const Duration(seconds: 5),
        ));
      }
    }
  }

  Widget _buildInfoRow(String label, String value, {Color? highlightColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 14)),
        if (highlightColor != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: highlightColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: highlightColor.withValues(alpha: 0.2)),
            ),
            child: Text(value, style: TextStyle(color: highlightColor, fontSize: 13, fontWeight: FontWeight.bold)),
          )
        else
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500)),
      ],
    );
  }
}
