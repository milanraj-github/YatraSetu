import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {

  
  static Future<Map<String, dynamic>> getMe() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/auth/me'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  static Future<Map<String, dynamic>> updateMe(String fullName) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/auth/me'),
        headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'},
        body: jsonEncode({'full_name': fullName}),
      ).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  static Future<Map<String, dynamic>> syncUser() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/auth/sync-user'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      final decoded = jsonDecode(response.body);
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return decoded; // Assuming it has {'success': true, 'data': ...}
      } else {
        String msg = decoded['detail'] is Map ? decoded['detail']['message'] : (decoded['detail'] ?? 'An error occurred');
        String code = decoded['detail'] is Map ? decoded['detail']['code'] : 'ERROR';
        return {'success': false, 'error': msg, 'code': code};
      }
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> ingestGps({
    required double latitude,
    required double longitude,
    required double speed,
    double heading = 0.0,
    double accuracy = 0.0,
  }) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/gps/ingest'),
        headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'latitude': latitude,
          'longitude': longitude,
          'speed': speed,
          'heading': heading,
          'accuracy': accuracy,
        })
      );
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }
  static const String baseUrl = 'http://192.168.31.193:8000/api/v1'; // Updated for Physical Android Phone
  static String? _authToken;

  static Future<void> persistToken(String token) async { _authToken = token; }
  static Future<void> clearToken() async { _authToken = null; }
  
  static Future<Map<String, dynamic>> studentLogin(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getStudentDashboard() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/dashboard'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getStudentBus() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/bus'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getStudentLiveBus() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/live-bus'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getMyAssignment() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/drivers/me/assignment'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }
  
  static Future<List<dynamic>> getActiveBuses() async {
    if (_authToken == null) return [];
    try {
      final response = await http.get(Uri.parse('$baseUrl/buses/active'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      return data['success'] ? data['data'] : [];
    } catch (e) { return []; }
  }

  static Future<Map<String, dynamic>> getTodaySchedules() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/drivers/me/schedules/today'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> startTrip(int sessionId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/drivers/me/trips/$sessionId/start'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> endTrip(int sessionId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/drivers/me/trips/$sessionId/end'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> sendLocation(Map<String, dynamic> loc) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/gps/ingest'), headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'}, body: jsonEncode(loc)).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> sendLocationBatch(List<Map<String, dynamic>> locs) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/gps/ingest/batch'), headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'}, body: jsonEncode({'locations': locs})).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getStopIntelligence() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/gps/stop-intelligence'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> confirmAccidentSafe(int alertId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/gps/emergency/$alertId/safe'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> sendManualSOS(String message) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/gps/emergency/sos'), headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'}, body: jsonEncode({'message': message})).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> registerDeviceToken(String token, {String? platform}) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/notifications/device-token'), headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'}, body: jsonEncode({'token': token, 'platform': platform})).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> deactivateDeviceToken(String token) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.delete(Uri.parse('$baseUrl/notifications/device-token/$token'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getUnreadNotificationCount() async { return getNotificationsUnreadCount(); }
  static Future<Map<String, dynamic>> getNotificationsUnreadCount() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/notifications/unread-count'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getNotifications() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/notifications'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> markNotificationRead(int id) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.patch(Uri.parse('$baseUrl/notifications/$id/read'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getTripHistory({int limit = 20}) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/drivers/me/trips/history?limit=$limit'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }
  
  static Future<Map<String, dynamic>> getStudentTripHistory({int page = 1, int pageSize = 20}) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/trips/history?page=$page&page_size=$pageSize'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getStudentTripDetail(int tripId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/trips/$tripId'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getActiveSafetyEvent() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/safety/active'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> updateProfile(String fullName, String? phoneNumber) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.patch(Uri.parse('$baseUrl/auth/profile'), headers: {'Authorization': 'Bearer $_authToken', 'Content-Type': 'application/json'}, body: jsonEncode({'full_name': fullName, 'phone_number': phoneNumber})).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> submitParentRequest(String studentEmail, String relationshipType) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/parents/request'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'student_email': studentEmail,
          'relationship_type': relationshipType,
        }),
      ).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getParentRequests() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/students/me/parent-requests'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> acceptParentRequest(int requestId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/students/me/parent-requests/$requestId/accept'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> rejectParentRequest(int requestId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.post(Uri.parse('$baseUrl/students/me/parent-requests/$requestId/reject'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> registerParentAccount(String firebaseToken, String registrationToken, String fullName) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/parents/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'firebase_token': firebaseToken,
          'registration_token': registrationToken,
          'full_name': fullName,
        }),
      ).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> verifyParentRequest(String token) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/parents/request/verify?token=$token')).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  
  static Future<Map<String, dynamic>> getMySafetyEvents() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/parents/me/safety'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  
  static Future<Map<String, dynamic>> getParentStudentTripHistory(int studentId, {int page = 1, int pageSize = 20}) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/parents/me/students/$studentId/trips/history?page=$page&page_size=$pageSize'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  static Future<Map<String, dynamic>> getMyStudents() async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/parents/me/students'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }

  static Future<Map<String, dynamic>> getParentLiveBus(int studentId) async {
    if (_authToken == null) return {'success': false, 'error': 'Not authenticated'};
    try {
      final response = await http.get(Uri.parse('$baseUrl/parents/me/students/$studentId/live-bus'), headers: {'Authorization': 'Bearer $_authToken'}).timeout(const Duration(seconds: 10));
      return jsonDecode(response.body);
    } catch (e) { return {'success': false, 'error': e.toString()}; }
  }
}
