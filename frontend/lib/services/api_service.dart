import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Local Mac IP address for physical phone testing (192.168.31.193)
  static const String baseUrl = 'http://192.168.31.193:8000/api/v1';


  static final Map<String, String> userTokens = {
    'driver1': 'mock-token-driver1@sode-edu.in',
    'driver2': 'mock-token-driver2@sode-edu.in',
    'driver3': 'mock-token-driver3@sode-edu.in',
    'student1': 'mock-token-student1@sode-edu.in',
    'admin1': 'mock-token-admin1@sode-edu.in',
  };

  static String currentRole = 'driver1';

  static String get currentToken => userTokens[currentRole] ?? userTokens['driver1']!;

  static Future<Map<String, dynamic>> syncUser() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/sync-user'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $currentToken',
        },
      );
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  static Future<List<dynamic>> getActiveBuses() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/tracking/active-buses'),
        headers: {
          'Authorization': 'Bearer $currentToken',
        },
      );
      final data = jsonDecode(response.body);
      if (data['success'] == true && data['data'] != null) {
        return data['data'];
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  static Future<Map<String, dynamic>> ingestGps({
    required double latitude,
    required double longitude,
    required double speed,
    double heading = 90.0,
    double accuracy = 3.0,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/gps/ingest'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $currentToken',
        },
        body: jsonEncode({
          'latitude': latitude,
          'longitude': longitude,
          'speed': speed,
          'heading': heading,
          'accuracy': accuracy,
          'recorded_at': DateTime.now().toUtc().toIso8601String(),
        }),
      );
      return jsonDecode(response.body);
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }
}
