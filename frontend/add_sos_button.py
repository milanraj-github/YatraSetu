import re

with open("lib/screens/driver_dashboard_screen.dart", "r") as f:
    content = f.read()

# Add _isSendingSOS state var
if "bool _isSendingSOS = false;" not in content:
    content = content.replace("bool _isConfirmingSafe = false;", "bool _isConfirmingSafe = false;\n  bool _isSendingSOS = false;")

# Insert the button in _buildScheduleCard
search_end_trip = """                    child: ElevatedButton(
                      onPressed: isActionLoading ? null : () => _confirmAction('End Trip?', 'END TRIP', sessionId, scheduleData, false),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      child: isActionLoading 
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('END TRIP', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1)),
                    ),
                  ),
                ],"""

replace_end_trip = """                    child: ElevatedButton(
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
                ],"""

content = content.replace(search_end_trip, replace_end_trip)

# Insert the dialog method
dialog_method = """
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
        _loadDashboardData(); // Refresh to pull active SOS state if needed
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res['error'] ?? 'Unable to send emergency. Check connection and try again.'),
          backgroundColor: Colors.orange,
          duration: const Duration(seconds: 5),
        ));
      }
    }
  }
"""

content = content.replace("  Widget _buildInfoRow", dialog_method + "\n  Widget _buildInfoRow")

# Also, if there is an active SOS, we should show a banner and hide the SEND SOS button.
# "If an active SOS already exists: Driver screen should display 🚨 EMERGENCY ACTIVE"
sos_banner = """
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
"""

content = content.replace("  Widget _buildBody() {", sos_banner + "\n  Widget _buildBody() {")

# Insert the banner into _buildNormalBody at the top
normal_body_search = """    return RefreshIndicator(
      onRefresh: _fetchDashboardData,
      color: const Color(0xFF3B82F6),
      backgroundColor: const Color(0xFF1E293B),
      child: ListView("""
normal_body_replace = normal_body_search + """
        padding: const EdgeInsets.all(16),
        children: [
          _buildActiveSOSBanner(),"""

# Wait, `ListView` in _buildNormalBody might already have `padding:`
listview_search = """      child: ListView(
        padding: const EdgeInsets.all(16),
        children: ["""
listview_replace = listview_search + """
          _buildActiveSOSBanner(),"""
          
if listview_search in content:
    content = content.replace(listview_search, listview_replace)

# Hide SEND SOS if SOS already active
sos_button_search = """                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isSendingSOS ? null : () => _showSOSDialog(),"""
sos_button_replace = """                  if (_stopIntelligence?['active_sos_id'] == null)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isSendingSOS ? null : () => _showSOSDialog(),"""
                      
content = content.replace(sos_button_search, sos_button_replace)


with open("lib/screens/driver_dashboard_screen.dart", "w") as f:
    f.write(content)

