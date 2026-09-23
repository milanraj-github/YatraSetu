import 'dart:async';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  factory DatabaseHelper() => _instance;
  DatabaseHelper._internal();

  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDb();
    return _database!;
  }

  Future<Database> _initDb() async {
    String dbPath = await getDatabasesPath();
    String path = join(dbPath, 'smartbus_offline_gps.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE offline_location_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL,
        longitude REAL,
        speed REAL,
        heading REAL,
        accuracy REAL,
        recorded_at TEXT,
        sync_status TEXT DEFAULT 'PENDING'
      )
    ''');
  }

  Future<int> insertLocation(Map<String, dynamic> locationData) async {
    final db = await database;
    
    // Maintain a max size of 10,000 to prevent infinite growth
    final count = Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM offline_location_queue')) ?? 0;
    if (count >= 10000) {
      // Don't insert more if queue is at absolute max, we should avoid getting here but protects device.
      return -1; 
    }

    return await db.insert('offline_location_queue', {
      'latitude': locationData['latitude'],
      'longitude': locationData['longitude'],
      'speed': locationData['speed'],
      'heading': locationData['heading'],
      'accuracy': locationData['accuracy'],
      'recorded_at': locationData['recorded_at'],
      'sync_status': 'PENDING'
    });
  }

  Future<List<Map<String, dynamic>>> getPendingLocations({int limit = 50}) async {
    final db = await database;
    return await db.query(
      'offline_location_queue',
      where: 'sync_status = ?',
      whereArgs: ['PENDING'],
      orderBy: 'recorded_at ASC',
      limit: limit,
    );
  }

  Future<void> deleteLocationsByTimestamps(List<String> timestamps) async {
    if (timestamps.isEmpty) return;
    final db = await database;
    
    // Create place holders for IN clause
    final placeholders = List.filled(timestamps.length, '?').join(',');
    
    await db.delete(
      'offline_location_queue',
      where: 'recorded_at IN ($placeholders)',
      whereArgs: timestamps,
    );
  }

  Future<int> getPendingCount() async {
    final db = await database;
    return Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM offline_location_queue WHERE sync_status = ?', ['PENDING'])
    ) ?? 0;
  }
}
