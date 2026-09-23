import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DriverProfileScreen extends StatefulWidget {
  final Map<String, dynamic> driverData;
  final Map<String, dynamic>? busData;

  const DriverProfileScreen({super.key, required this.driverData, this.busData});

  @override
  State<DriverProfileScreen> createState() => _DriverProfileScreenState();
}

class _DriverProfileScreenState extends State<DriverProfileScreen> {
  bool _isEditing = false;
  bool _isSaving = false;
  
  late TextEditingController _nameController;
  late TextEditingController _phoneController;

  late String _fullName;
  String? _phoneNumber;
  late String _email;
  late String _role;
  late String _status;

  @override
  void initState() {
    super.initState();
    _populateData(widget.driverData);
  }

  void _populateData(Map<String, dynamic> data) {
    _fullName = data['full_name'] ?? 'Unknown';
    _phoneNumber = data['phone_number'];
    _email = data['email'] ?? 'No email';
    _role = data['role'] ?? 'DRIVER';
    _status = data['status'] ?? 'UNKNOWN';

    _nameController = TextEditingController(text: _fullName);
    _phoneController = TextEditingController(text: _phoneNumber ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    final newName = _nameController.text.trim();
    final newPhone = _phoneController.text.trim();

    if (newName.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Full Name cannot be empty')));
      return;
    }

    setState(() => _isSaving = true);
    
    final res = await ApiService.updateProfile(
      newName, 
      newPhone.isEmpty ? null : newPhone
    );

    if (!mounted) return;
    setState(() => _isSaving = false);

    if (res['success'] == true && res['data'] != null && res['data']['user'] != null) {
      setState(() {
        _populateData(res['data']['user']);
        _isEditing = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated successfully'), backgroundColor: Colors.green)
      );
      // Let dashboard know to refresh when we pop (just pop with true)
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['error'] ?? 'Unable to update profile. Please try again.'), backgroundColor: Colors.red)
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        Navigator.pop(context, true);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Driver Profile'),
          backgroundColor: const Color(0xFF1E293B),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.pop(context, true),
          ),
        ),
        backgroundColor: const Color(0xFF0F172A),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 16),
              const CircleAvatar(
                radius: 40,
                backgroundColor: Color(0xFF334155),
                child: Icon(Icons.person, size: 50, color: Colors.white),
              ),
              const SizedBox(height: 24),
              
              if (_isEditing)
                _buildEditForm()
              else
                _buildReadView(),
                
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReadView() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildInfoRow('Full Name', _fullName, Icons.badge),
          const Divider(color: Color(0xFF334155), height: 32),
          _buildInfoRow('Email', _email, Icons.email),
          const Divider(color: Color(0xFF334155), height: 32),
          _buildInfoRow('Phone', _phoneNumber ?? 'Not provided', Icons.phone),
          const Divider(color: Color(0xFF334155), height: 32),
          _buildInfoRow('Role', _role, Icons.security, color: Colors.blue),
          const Divider(color: Color(0xFF334155), height: 32),
          _buildInfoRow('Account Status', _status, Icons.verified_user, color: _status == 'ACTIVE' ? Colors.green : Colors.red),
          
          if (widget.busData != null) ...[
            const Divider(color: Color(0xFF334155), height: 32),
            _buildInfoRow('Assigned Bus', widget.busData!['bus_number'] ?? 'Unknown', Icons.directions_bus),
            const Divider(color: Color(0xFF334155), height: 32),
            _buildInfoRow('Registration', widget.busData!['registration_number'] ?? 'Unknown', Icons.pin),
          ],
          
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => setState(() => _isEditing = true),
              icon: const Icon(Icons.edit),
              label: const Text('EDIT PROFILE'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(color: Color(0xFF3B82F6)),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildEditForm() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Editable Fields', style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          _buildTextField('Full Name', _nameController, Icons.badge),
          const SizedBox(height: 24),
          _buildTextField('Phone Number', _phoneController, Icons.phone, keyboardType: TextInputType.phone),
          
          const SizedBox(height: 32),
          const Text('Read-Only Fields', style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          _buildInfoRow('Email', _email, Icons.email),
          const Divider(color: Color(0xFF334155), height: 24),
          _buildInfoRow('Role', _role, Icons.security, color: Colors.blue),
          if (widget.busData != null) ...[
            const Divider(color: Color(0xFF334155), height: 24),
            _buildInfoRow('Assigned Bus', widget.busData!['bus_number'] ?? 'Unknown', Icons.directions_bus),
          ],
          
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _isSaving ? null : _saveProfile,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF3B82F6),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: _isSaving 
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text('SAVE CHANGES', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1)),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: _isSaving ? null : () {
                setState(() {
                  _isEditing = false;
                  _nameController.text = _fullName;
                  _phoneController.text = _phoneNumber ?? '';
                });
              },
              style: TextButton.styleFrom(
                foregroundColor: Colors.white70,
              ),
              child: const Text('CANCEL'),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, IconData icon, {TextInputType? keyboardType}) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
        prefixIcon: Icon(icon, color: const Color(0xFF94A3B8)),
        enabledBorder: OutlineInputBorder(
          borderSide: const BorderSide(color: Color(0xFF334155)),
          borderRadius: BorderRadius.circular(8),
        ),
        focusedBorder: OutlineInputBorder(
          borderSide: const BorderSide(color: Color(0xFF3B82F6)),
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, IconData icon, {Color? color}) {
    return Row(
      children: [
        Icon(icon, color: Colors.white54, size: 20),
        const SizedBox(width: 12),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 14)),
        const Spacer(),
        Text(value, style: TextStyle(color: color ?? Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
