import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/firebase_auth_service.dart';
import 'role_selection_screen.dart';
import 'parent_live_bus_screen.dart';

class ParentPortalScreen extends StatefulWidget {
  final Map<String, dynamic>? userProfile;

  const ParentPortalScreen({super.key, this.userProfile});

  @override
  State<ParentPortalScreen> createState() => _ParentPortalScreenState();
}

class _ParentPortalScreenState extends State<ParentPortalScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<dynamic> _students = [];
  Map<String, dynamic>? _profile;
  int? _selectedStudentIndex;

  @override
  void initState() {
    super.initState();
    _profile = widget.userProfile;
    _fetchData();
  }

  Future<void> _fetchData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      if (_profile == null) {
        final profileRes = await ApiService.syncUser();
        if (profileRes['success'] == true) {
          _profile = profileRes['data']['user'];
        }
      }

      final res = await ApiService.getMyStudents();
      if (res['success'] == true) {
        setState(() {
          _students = res['data']['students'];
          _isLoading = false;
          if (_students.isNotEmpty && _selectedStudentIndex == null) {
            _selectedStudentIndex = 0;
          }
        });
      } else {
        setState(() {
          _errorMessage = res['error']?.toString() ?? 'Failed to load students.';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _logout() async {
    await FirebaseAuthService().signOut();
    if (mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const RoleSelectionScreen()),
        (route) => false,
      );
    }
  }

  Widget _buildProfileHeader() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        border: Border(bottom: BorderSide(color: Color(0xFF334155), width: 1)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
            child: const Icon(Icons.person, color: Color(0xFF10B981), size: 30),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Good Morning, ${_profile?['full_name']?.split(' ')[0] ?? 'Parent'}',
                  style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  _profile?['email'] ?? '',
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 14),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStudentCard(Map<String, dynamic> studentData) {
    final student = studentData['student'];
    final bus = studentData['bus'];
    final relationship = studentData['relationship_type'];

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.school, color: Color(0xFF38BDF8), size: 24),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          student['full_name'] ?? 'Unknown Student',
                          style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          student['email'] ?? '',
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                        ),
                      ],
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF38BDF8).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    relationship,
                    style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Divider(color: Color(0xFF334155), height: 1),
            ),
            if (bus != null) ...[
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.directions_bus, color: Color(0xFF10B981), size: 24),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Assigned Bus', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                        const SizedBox(height: 2),
                        Text(
                          '${bus['bus_number']}',
                          style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: bus['status'] == 'ACTIVE' ? const Color(0xFF10B981).withValues(alpha: 0.1) : Colors.orange.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      bus['status'] ?? 'UNKNOWN',
                      style: TextStyle(
                        color: bus['status'] == 'ACTIVE' ? const Color(0xFF10B981) : Colors.orange,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Registration: ${bus['registration_number']}',
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
              ),
            ] else ...[
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.orange.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.directions_bus_filled_outlined, color: Colors.orange, size: 24),
                  ),
                  const SizedBox(width: 16),
                  const Text(
                    'No bus assigned to this student.',
                    style: TextStyle(color: Colors.orange, fontSize: 14),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ParentLiveBusScreen(
                        studentId: student['id'],
                        studentName: student['full_name'],
                      ),
                    ),
                  );
                },
                icon: const Icon(Icons.map, color: Colors.white),
                label: const Text('Track Bus', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
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
        title: const Text('Parent Portal', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _fetchData,
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white),
            onPressed: _logout,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _fetchData,
        color: const Color(0xFF10B981),
        backgroundColor: const Color(0xFF1E293B),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            if (_profile != null) _buildProfileHeader(),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'My Students',
                        style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      if (!_isLoading && _students.isNotEmpty)
                        Text(
                          '${_students.length} Student${_students.length == 1 ? '' : 's'}',
                          style: const TextStyle(color: Color(0xFF10B981), fontSize: 14, fontWeight: FontWeight.bold),
                        ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  if (_isLoading)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.all(40.0),
                        child: CircularProgressIndicator(color: Color(0xFF10B981)),
                      ),
                    )
                  else if (_errorMessage != null)
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(40.0),
                        child: Column(
                          children: [
                            const Icon(Icons.error_outline, color: Colors.red, size: 48),
                            const SizedBox(height: 16),
                            Text(_errorMessage!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red)),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _fetchData,
                              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                              child: const Text('RETRY', style: TextStyle(color: Colors.white)),
                            )
                          ],
                        ),
                      ),
                    )
                  else if (_students.isEmpty)
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(40.0),
                        child: Column(
                          children: [
                            Icon(Icons.people_outline, color: const Color(0xFF94A3B8).withValues(alpha: 0.5), size: 64),
                            const SizedBox(height: 16),
                            const Text(
                              'No students are currently linked to your account.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 16),
                            ),
                          ],
                        ),
                      ),
                    )
                  else ...[
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: List.generate(_students.length, (index) {
                          final isSelected = _selectedStudentIndex == index;
                          return Padding(
                            padding: const EdgeInsets.only(right: 12.0),
                            child: ChoiceChip(
                              label: Text(_students[index]['student']['full_name']),
                              selected: isSelected,
                              onSelected: (selected) {
                                if (selected) {
                                  setState(() => _selectedStudentIndex = index);
                                }
                              },
                              selectedColor: const Color(0xFF10B981).withValues(alpha: 0.2),
                              backgroundColor: const Color(0xFF1E293B),
                              labelStyle: TextStyle(
                                color: isSelected ? const Color(0xFF10B981) : Colors.white,
                                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                              ),
                              side: BorderSide(
                                color: isSelected ? const Color(0xFF10B981) : const Color(0xFF334155),
                              ),
                            ),
                          );
                        }),
                      ),
                    ),
                    const SizedBox(height: 24),
                    const Text('Selected Student', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 14)),
                    const SizedBox(height: 12),
                    if (_selectedStudentIndex != null && _selectedStudentIndex! < _students.length)
                      _buildStudentCard(_students[_selectedStudentIndex!]),
                  ]
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}