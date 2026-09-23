import 'dart:async';
import 'package:geolocator/geolocator.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'api_service.dart';
import 'database_helper.dart';

class LocationService {
  static final LocationService _instance = LocationService._internal();
  factory LocationService() => _instance;
  LocationService._internal() {
    _initConnectivity();
  }

  StreamSubscription<Position>? _positionStream;
  
  
  bool _isTracking = false;
  String _statusMessage = 'Inactive';
  DateTime? _lastSuccessfulUpload;
  bool _isOnline = true;
int _queuedCount = 0;
  bool _isSyncing = false;
  Timer? _syncTimer;
  Timer? _intelTimer;
  Map<String, dynamic>? _stopIntelligence;
  
  final DatabaseHelper _dbHelper = DatabaseHelper();

  // Callback to update UI
  Function(String status, DateTime? lastUpload, String? error, bool isOnline, int queuedCount, bool isSyncing, Map<String, dynamic>? stopIntelligence)? onStatusChanged;

  bool get isTracking => _isTracking;
  String get statusMessage => _statusMessage;
  DateTime? get lastSuccessfulUpload => _lastSuccessfulUpload;
  int get queuedCount => _queuedCount;

  void _initConnectivity() {
    Connectivity().checkConnectivity().then(_updateConnectionStatus);
    var _connectivityStream = Connectivity().onConnectivityChanged.listen(_updateConnectionStatus);
  }

  Future<void> _updateConnectionStatus(List<ConnectivityResult> results) async {
    final result = results.firstOrNull ?? ConnectivityResult.none;
    bool wasOffline = !_isOnline;
    _isOnline = (result == ConnectivityResult.mobile || result == ConnectivityResult.wifi || result == ConnectivityResult.ethernet);
    
    if (wasOffline && _isOnline) {
      _triggerSync();
    }
    
    _queuedCount = await _dbHelper.getPendingCount();
    _notifyUI();
  }

  Future<bool> requestPermission() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      _updateStatus('GPS Disabled', error: 'Please turn on location services to continue trip tracking.');
      return false;
    }

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        _updateStatus('Permission Denied', error: 'Location permission is required to track the active trip.');
        return false;
      }
    }
    
    if (permission == LocationPermission.deniedForever) {
      _updateStatus('Permission Denied', error: 'Location permissions are permanently denied. Please enable them in settings.');
      return false;
    } 

    return true;
  }

  Future<void> startTracking() async {
    if (_isTracking) return;
    
    _updateStatus('Starting GPS...');
    
    final hasPermission = await requestPermission();
    if (!hasPermission) return;

    _isTracking = true;
    _updateStatus('GPS ACTIVE');
    _queuedCount = await _dbHelper.getPendingCount();
    _notifyUI();
    
    const LocationSettings locationSettings = LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 10,
    );

    _positionStream = Geolocator.getPositionStream(locationSettings: locationSettings).listen(
      (Position position) {
        _handleLocationUpdate(position);
      },
      onError: (e) {
        _updateStatus('GPS Error', error: 'Location stream encountered an error.');
      }
    );
    
    // Periodically sync if items are stuck
    _intelTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (_isOnline && _isTracking) _fetchStopIntelligence();
    });
    
    _syncTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (_isOnline && _queuedCount > 0 && !_isSyncing) {
        _triggerSync();
      }
    });
    
    // Also trigger initial sync just in case
    _triggerSync();
  }

  void stopTracking() {
    _isTracking = false;
    _positionStream?.cancel();
    _positionStream = null;
    _syncTimer?.cancel();
    _syncTimer = null;
    _intelTimer?.cancel();
    _intelTimer = null;
    _stopIntelligence = null;
    _lastSuccessfulUpload = null;
    _updateStatus('Inactive');
  }

  Future<void> _handleLocationUpdate(Position position) async {
    if (!_isTracking) return;
    
    double speedKmH = position.speed * 3.6;
    if (speedKmH < 0) speedKmH = 0.0;

    final locationData = {
      "latitude": position.latitude,
      "longitude": position.longitude,
      "speed": speedKmH,
      "heading": position.heading >= 0 ? position.heading : 0.0,
      "accuracy": position.accuracy,
      "recorded_at": position.timestamp.toUtc().toIso8601String(),
    };

    if (_isOnline) {
      final res = await ApiService.sendLocation(locationData);
      if (res['success'] == true) {
        _lastSuccessfulUpload = DateTime.now();
        _updateStatus('GPS ACTIVE');
      } else {
        // Fallback to queue if API fails
        await _queueLocation(locationData);
      }
    } else {
      // Offline -> queue
      await _queueLocation(locationData);
    }
  }

  Future<void> _queueLocation(Map<String, dynamic> locationData) async {
    await _dbHelper.insertLocation(locationData);
    _queuedCount = await _dbHelper.getPendingCount();
    _updateStatus('GPS ACTIVE');
  }

  Future<void> _triggerSync() async {
    if (_isSyncing || !_isOnline) return;
    
    _queuedCount = await _dbHelper.getPendingCount();
    if (_queuedCount == 0) return;
    
    _isSyncing = true;
    _notifyUI();

    try {
      while (true) {
        final pending = await _dbHelper.getPendingLocations(limit: 50);
        if (pending.isEmpty) break;
        
        final batch = pending.map((p) => {
          "latitude": p['latitude'],
          "longitude": p['longitude'],
          "speed": p['speed'],
          "heading": p['heading'],
          "accuracy": p['accuracy'],
          "recorded_at": p['recorded_at'],
        }).toList();

        final res = await ApiService.sendLocationBatch(batch);
        if (res['success'] == true) {
          final data = res['data'];
          if (data != null && data['synced_points'] != null) {
             List<dynamic> synced = data['synced_points'];
             List<String> timestamps = synced.map((t) => t.toString()).toList();
             await _dbHelper.deleteLocationsByTimestamps(timestamps);
             _lastSuccessfulUpload = DateTime.now();
          }
          // Also handle failed_points if they are permanently rejected (e.g. invalid), but for now we keep it simple.
          // In a real app we might drop them to prevent infinite retry loop on bad data.
        } else {
          // If network failed during batch, abort sync loop
          break;
        }
      }
    } catch (e) {
      // ignore
    } finally {
      _queuedCount = await _dbHelper.getPendingCount();
      _isSyncing = false;
      _notifyUI();
    }
  }

  
  Future<void> _fetchStopIntelligence() async {
    final res = await ApiService.getStopIntelligence();
    if (res['success'] == true && res['data'] != null) {
      _stopIntelligence = res['data'];
      _notifyUI();
    }
  }

  void _updateStatus(String status, {String? error}) {
    _statusMessage = status;
    _notifyUI(error: error);
  }

  void _notifyUI({String? error}) {
    if (onStatusChanged != null) {
      onStatusChanged!(_statusMessage, _lastSuccessfulUpload, error, _isOnline, _queuedCount, _isSyncing, _stopIntelligence);
    }
  }
}
