import 'package:flutter/material.dart';
import '../services/api_service.dart';

class StudentParentRequestsScreen extends StatefulWidget {
  const StudentParentRequestsScreen({super.key});

  @override
  State<StudentParentRequestsScreen> createState() => _StudentParentRequestsScreenState();
}

class _StudentParentRequestsScreenState extends State<StudentParentRequestsScreen> {
  List<dynamic> _requests = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchRequests();
  }

  Future<void> _fetchRequests() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final res = await ApiService.getParentRequests();
      if (res['success'] == true) {
        setState(() { _requests = res['data']['requests'] ?? []; });
      } else {
        setState(() { _error = res['error']?.toString(); });
      }
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _isLoading = false; });
    }
  }

  Future<void> _handleAction(int id, bool accept) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6))),
    );

    try {
      final res = accept 
          ? await ApiService.acceptParentRequest(id)
          : await ApiService.rejectParentRequest(id);
          
      if (mounted) {
        Navigator.of(context).pop(); // dismiss loading
        if (res['success'] == true) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['data']?['message'] ?? 'Success'), backgroundColor: Colors.green));
          _fetchRequests();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res['error']?['message'] ?? 'Action failed'), backgroundColor: Colors.red));
        }
      }
    } catch (e) {
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()), backgroundColor: Colors.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Parent / Guardian Requests', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E293B),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
        : _error != null 
          ? Center(child: Text(_error!, style: const TextStyle(color: Colors.redAccent)))
          : _requests.isEmpty 
            ? const Center(child: Text('No pending requests.', style: TextStyle(color: Colors.white54, fontSize: 16)))
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: _requests.length,
                itemBuilder: (context, index) {
                  final req = _requests[index];
                  return Card(
                    color: const Color(0xFF1E293B),
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.family_restroom, color: Color(0xFFF59E0B)),
                              const SizedBox(width: 8),
                              Text('Relationship: ${req['relationship_type']}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text('Requested: ${DateTime.parse(req['created_at']).toLocal().toString().split('.')[0]}', style: const TextStyle(color: Colors.white54, fontSize: 13)),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: ElevatedButton(
                                  style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                                  onPressed: () => _handleAction(req['id'], true),
                                  child: const Text('ACCEPT', style: TextStyle(color: Colors.white)),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: ElevatedButton(
                                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                                  onPressed: () => _handleAction(req['id'], false),
                                  child: const Text('REJECT', style: TextStyle(color: Colors.white)),
                                ),
                              ),
                            ],
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
