# UI/UX & Technical Design

## Visual Design
- **Theme:** Dark mode primary theme (`Color(0xFF0F172A)` background) with bright, contrast-heavy accents.
- **Accents:** 
  - Primary Action / Success: Green (`Color(0xFF10B981)`)
  - Secondary Action / Brand: Blue (`Color(0xFF3B82F6)`)
  - Warnings / Emergency: Red / Orange

## App Navigation Structure
1. **Splash Screen:** Checks auth state.
2. **Auth Screen:** Login, Google Sign-In, Role selection (Parent Sign Up).
3. **Role Portals:**
   - **Student Main Screen:** Home (Dashboard), Live Bus, Alerts, Trips, Profile.
   - **Parent Main Screen:** Home (My Students), Safety, Alerts, Profile.
   - **Driver Main Screen:** Dashboard, Live Route, Alerts, SOS, Profile.

## Database Schema Design Notes
- Uses cascading deletes for foreign keys (e.g., deleting a User deletes their Assignments).
- Strict constraints: A Parent-Student relationship is unique. A User can only have one active Bus Assignment at a time.
