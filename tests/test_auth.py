"""
tests/test_auth.py
Tests for Flask-Login authentication and Role-Based Access Control
Run with: pytest tests/test_auth.py -v
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from dashboard import app, db, bcrypt, USERS, get_user_by_username

# ── Setup ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def login(client, username, password):
    """Helper function to log in."""
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def logout(client):
    """Helper function to log out."""
    return client.get('/logout', follow_redirects=True)

# ── User Model Tests ──────────────────────────────────────────────────────────
def test_users_exist():
    """All 3 users should exist in USERS dict."""
    assert get_user_by_username('admin') is not None
    assert get_user_by_username('engineer') is not None
    assert get_user_by_username('viewer') is not None
    print("PASS: All 3 users exist")

def test_user_roles():
    """Each user should have the correct role."""
    assert USERS['1'].role == 'admin'
    assert USERS['2'].role == 'engineer'
    assert USERS['3'].role == 'viewer'
    print("PASS: User roles are correct")

def test_admin_permissions():
    """Admin should have all permissions."""
    admin = get_user_by_username('admin')
    assert admin.is_admin()    == True
    assert admin.is_engineer() == True
    print("PASS: Admin has correct permissions")

def test_engineer_permissions():
    """Engineer should have engineer but not admin permissions."""
    engineer = get_user_by_username('engineer')
    assert engineer.is_admin()    == False
    assert engineer.is_engineer() == True
    print("PASS: Engineer has correct permissions")

def test_viewer_permissions():
    """Viewer should have no action permissions."""
    viewer = get_user_by_username('viewer')
    assert viewer.is_admin()    == False
    assert viewer.is_engineer() == False
    print("PASS: Viewer has correct permissions")

def test_password_hashing():
    """Passwords should be bcrypt hashed, not plain text."""
    admin = get_user_by_username('admin')
    assert admin.password_hash != 'admin123'
    assert admin.check_password('admin123') == True
    assert admin.check_password('wrongpassword') == False
    print("PASS: Password hashing works correctly")

# ── Login / Logout Tests ──────────────────────────────────────────────────────
def test_login_page_loads(client):
    """Login page should return 200."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign In' in response.data
    print("PASS: Login page loads correctly")

def test_login_with_valid_admin(client):
    """Admin should be able to log in successfully."""
    response = login(client, 'admin', 'admin123')
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Incident' in response.data
    print("PASS: Admin login successful")

def test_login_with_valid_engineer(client):
    """Engineer should be able to log in successfully."""
    response = login(client, 'engineer', 'eng123')
    assert response.status_code == 200
    print("PASS: Engineer login successful")

def test_login_with_valid_viewer(client):
    """Viewer should be able to log in successfully."""
    response = login(client, 'viewer', 'view123')
    assert response.status_code == 200
    print("PASS: Viewer login successful")

def test_login_with_wrong_password(client):
    """Login with wrong password should fail."""
    response = login(client, 'admin', 'wrongpassword')
    assert b'Invalid' in response.data
    print("PASS: Wrong password rejected correctly")

def test_login_with_unknown_user(client):
    """Login with unknown username should fail."""
    response = login(client, 'unknownuser', 'password123')
    assert b'Invalid' in response.data
    print("PASS: Unknown user rejected correctly")

def test_logout(client):
    """User should be able to log out."""
    login(client, 'admin', 'admin123')
    response = logout(client)
    assert response.status_code == 200
    print("PASS: Logout works correctly")

# ── Protected Route Tests ─────────────────────────────────────────────────────
def test_dashboard_requires_login(client):
    """Dashboard should redirect to login if not authenticated."""
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
    print("PASS: Dashboard redirects unauthenticated users")

def test_dashboard_accessible_after_login(client):
    """Dashboard should be accessible after login."""
    login(client, 'admin', 'admin123')
    response = client.get('/dashboard')
    assert response.status_code == 200
    print("PASS: Dashboard accessible after login")

def test_api_incidents_requires_login(client):
    """API incidents endpoint should require login."""
    response = client.get('/api/incidents')
    assert response.status_code in [302, 401]
    print("PASS: API requires authentication")

def test_run_pipeline_requires_admin(client):
    """Run pipeline API should reject non-admin users."""
    login(client, 'viewer', 'view123')
    response = client.post('/api/run-pipeline')
    data = response.get_json()
    assert response.status_code == 403
    assert 'Admin' in data['error']
    print("PASS: Pipeline correctly blocked for viewer")

def test_run_pipeline_requires_admin_engineer(client):
    """Run pipeline API should reject engineer users too."""
    login(client, 'engineer', 'eng123')
    response = client.post('/api/run-pipeline')
    assert response.status_code == 403
    print("PASS: Pipeline correctly blocked for engineer")

def test_viewer_can_access_incidents(client):
    """Viewer should be able to read incidents."""
    login(client, 'viewer', 'view123')
    response = client.get('/api/incidents')
    assert response.status_code == 200
    print("PASS: Viewer can read incidents")

def test_root_redirects_to_login(client):
    """Root URL should redirect unauthenticated users to login."""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    print("PASS: Root redirects to login correctly")