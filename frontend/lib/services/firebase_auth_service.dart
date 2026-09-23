import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'api_service.dart';

class FirebaseAuthService {
  FirebaseAuth get _auth => FirebaseAuth.instance;

  Future<User?> getCurrentUser() async {
    return _auth.currentUser;
  }

  Future<String?> getIdToken(bool forceRefresh) async {
    final user = _auth.currentUser;
    if (user != null) {
      return await user.getIdToken(forceRefresh);
    }
    return null;
  }

  
  Future<Map<String, dynamic>> signUpWithEmail(String email, String password, String name) async {
    try {
      UserCredential cred = await _auth.createUserWithEmailAndPassword(email: email, password: password);
      if (cred.user != null) {
        await cred.user!.updateDisplayName(name);
        final token = await cred.user!.getIdToken();
        if (token != null) {
          await ApiService.persistToken(token);
        }
        return {'success': true, 'user': cred.user};
      }
      return {'success': false, 'error': 'Unknown error occurred during sign up.'};
    } on FirebaseAuthException catch (e) {
      String msg = 'Authentication failed.';
      if (e.code == 'weak-password') msg = 'The password provided is too weak.';
      else if (e.code == 'email-already-in-use') msg = 'An account already exists for that email.';
      else if (e.code == 'invalid-email') msg = 'The email address is invalid.';
      return {'success': false, 'error': msg};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> signInWithEmail(String email, String password) async {
    try {
      debugPrint('Firebase login attempt for email: $email');
      
      final UserCredential credential = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      
      debugPrint('Firebase result: SUCCESS for $email');

      final token = await credential.user?.getIdToken();
      if (token != null) {
        await ApiService.persistToken(token);
        return {'success': true, 'user': credential.user};
      }
      return {'success': false, 'error': 'Failed to retrieve token'};
    } on FirebaseAuthException catch (e) {
      debugPrint('Firebase result: FAILURE. Error Code: ${e.code}');
      
      String errorMsg;
      switch (e.code) {
        case 'user-not-found':
          errorMsg = 'Driver account was not found.';
          break;
        case 'wrong-password':
          errorMsg = 'Incorrect password.';
          break;
        case 'invalid-credential':
          errorMsg = 'Email or password is incorrect.';
          break;
        case 'invalid-email':
          errorMsg = 'The email address is invalid.';
          break;
        case 'user-disabled':
          errorMsg = 'This Driver account has been disabled.';
          break;
        case 'too-many-requests':
          errorMsg = 'Too many login attempts. Please try again later.';
          break;
        case 'network-request-failed':
          errorMsg = 'Unable to connect. Check your internet connection.';
          break;
        default:
          errorMsg = e.message ?? 'An unknown error occurred.';
      }
      return {'success': false, 'error': errorMsg, 'code': e.code};
    } catch (e) {
      debugPrint('Firebase result: FAILURE. Exception: $e');
      return {'success': false, 'error': 'Unable to connect to SMARTBUS.'};
    }
  }

  Future<Map<String, dynamic>> signInWithGoogle() async {
    try {
            // Initialize with serverClientId for Android to receive an ID token
      await GoogleSignIn.instance.initialize(
        serverClientId: '348875670834-hmdr024g8brhknimsbr0j0lf9oigdd9o.apps.googleusercontent.com',
      );
      final GoogleSignInAccount? googleUser = await GoogleSignIn.instance.authenticate();
      
      if (googleUser == null) {
        return {'success': false, 'error': 'Sign in aborted by user'}; // Handled smoothly by UI
      }
      
      final GoogleSignInAuthentication googleAuth = googleUser.authentication;
      final AuthCredential credential = GoogleAuthProvider.credential(
        accessToken: null,
        idToken: googleAuth.idToken,
      );
      
      UserCredential userCredential = await _auth.signInWithCredential(credential);
      
      final token = await userCredential.user?.getIdToken();
      if (token != null) {
        await ApiService.persistToken(token);
        return {'success': true, 'user': userCredential.user};
      }
      
      return {'success': false, 'error': 'Failed to retrieve token from Firebase.'};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> resetPassword(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email.trim());
      return {'success': true};
    } on FirebaseAuthException catch (e) {
      return {'success': false, 'error': e.message ?? 'Error resetting password'};
    }
  }

  Future<void> signOut() async {
    await _auth.signOut();
    await ApiService.clearToken();
  }

  Future<void> deleteCurrentUser() async {
    try {
      await _auth.currentUser?.delete();
    } catch (e) {
      debugPrint("Failed to delete user: $e");
    }
  }
}
