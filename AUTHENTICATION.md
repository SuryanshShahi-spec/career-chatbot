# 🔐 Streamlit App with Login & Signup

## Overview
The Job Search AI Agent now includes full authentication with login and signup pages.

## Features Added

### 1. **Login Page** (`render_login_page()`)
- Clean, centered UI with email and password fields
- Direct login with existing credentials
- Quick link to sign up for new users
- Error handling with helpful messages

### 2. **Signup Page** (`render_signup_page()`)
- Full registration form with:
  - Full Name
  - Email
  - Password (with validation: min 8 chars, uppercase, lowercase, digit)
  - Confirm Password
  - Phone (optional)
- Input validation before submission
- Automatic redirect to login on successful registration

### 3. **Authenticated Chat Interface**
- Shows user email in sidebar
- Logout button to return to login
- Same AI agent functionality as before
- Session-based authentication state

### 4. **Authentication Flow**
```
User visits app
    ↓
Check session_state.authenticated
    ↓
If False → Show Login/Signup pages
If True → Show Chat Interface
    ↓
User logs in/signs up
    ↓
Set session_state.token, user_id, user_email
    ↓
Redirect to chat interface
```

## Setup Instructions

### 1. Initialize Database
Before running the app, initialize the PostgreSQL database:
```bash
python -c "from Assets.auth import auth_service; from Data.postgre import init_db; init_db()"
```

### 2. Ensure Environment Variables
Make sure your `.env` file includes:
```
DB_NAME=user_auth
DB_USER=postgres
DB_PASSWORD=<your_password>
DB_HOST=localhost
DB_PORT=5432
JWT_SECRET=<your_secret_key>
GROQ_API_KEY=<your_key>
```

### 3. Run the App
```bash
streamlit run Agent/app_auth.py
```

## Files Modified/Created

- **app_auth.py** - New authenticated version of the Streamlit app
- **app_backup.py** - Backup of the original app.py (if created)

## Integration with Existing Auth
The app integrates with:
- `Assets/auth.py` - Authentication service facade
- `Data/postgre.py` - PostgreSQL database layer
- Session state management for user data

## Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

## Testing

### Test Registration
1. Click "Sign Up"
2. Fill in details:
   - Full Name: Test User
   - Email: test@example.com
   - Password: TestPass123
   - Confirm Password: TestPass123
3. Click "Create Account"

### Test Login
1. From login page, enter:
   - Email: test@example.com
   - Password: TestPass123
2. Click "Login"

### Test Logout
1. Click "🚪 Logout" in sidebar
2. You'll be redirected to login page

## Features to Extend

1. **Profile Picture Upload** - Update frontend to support profile picture
2. **Password Reset** - Add "Forgot Password?" flow
3. **Email Verification** - Verify emails before account activation
4. **Two-Factor Authentication** - Add 2FA support
5. **User Profile Page** - View and edit full profile details
6. **Session Persistence** - Store tokens in browser/local storage
7. **Social Login** - Add Google/GitHub authentication
