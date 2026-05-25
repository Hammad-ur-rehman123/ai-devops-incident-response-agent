"""
tests/test_api.py
Tests for API endpoints, database, search/filter and CSV export
Run with: pytest tests/test_api.py -v
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from dashboard import app, db, Incident

# ── Setup ─────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def clean_db():
    """Fresh empty database for EVERY test — runs automatically."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        yield client

@pytest.fixture
def admin_client(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    return client

@pytest.fixture
def viewer_client(client):
    client.post('/login', data={'username': 'viewer', 'password': 'view123'})
    return client

def add_test_incident(severity='HIGH', root_cause='Test CPU spike', jira='TEST-001', service='test-service'):
    with app.app_context():
        inc = Incident(
            root_cause   = root_cause,
            severity     = severity,
            jira_ticket  = jira,
            status       = 'resolved',
            triggered_by = 'test',
            service_name = service,
        )
        db.session.add(inc)
        db.session.commit()

# ── Database Model Tests ──────────────────────────────────────────────────────
def test_incident_model_creates_correctly():
    with app.app_context():
        inc = Incident(
            root_cause   = 'High CPU usage detected',
            severity     = 'CRITICAL',
            jira_ticket  = 'KAN-001',
            status       = 'resolved',
            triggered_by = 'admin',
            service_name = 'ec2-instance',
        )
        db.session.add(inc)
        db.session.commit()
        saved = Incident.query.first()
        assert saved.root_cause  == 'High CPU usage detected'
        assert saved.severity    == 'CRITICAL'
        assert saved.jira_ticket == 'KAN-001'
        assert saved.id is not None
        print("PASS: Incident model saves and retrieves correctly")

def test_incident_to_dict():
    with app.app_context():
        inc = Incident(root_cause='Test', severity='HIGH',
                       jira_ticket='TEST-1', triggered_by='admin', service_name='web')
        db.session.add(inc)
        db.session.commit()
        d = inc.to_dict()
        assert 'id'           in d
        assert 'time'         in d
        assert 'root_cause'   in d
        assert 'severity'     in d
        assert 'jira_ticket'  in d
        assert 'triggered_by' in d
        assert 'service_name' in d
        print("PASS: to_dict() returns all required fields")

def test_incident_default_jira_ticket():
    with app.app_context():
        inc = Incident(root_cause='Test', severity='LOW')
        db.session.add(inc)
        db.session.commit()
        assert inc.to_dict()['jira_ticket'] == 'N/A'
        print("PASS: Missing jira_ticket defaults to N/A")

# ── API: GET /api/incidents ───────────────────────────────────────────────────
def test_get_incidents_empty(admin_client):
    response = admin_client.get('/api/incidents')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 0
    assert data['incidents'] == []
    print("PASS: Empty incidents returns correctly")

def test_get_incidents_returns_data(admin_client):
    add_test_incident('CRITICAL', 'CPU spike',   'KAN-001')
    add_test_incident('HIGH',     'Memory leak', 'KAN-002')
    response = admin_client.get('/api/incidents')
    data = response.get_json()
    assert data['total'] == 2
    assert len(data['incidents']) == 2
    print("PASS: Incidents returned from database correctly")

def test_get_incidents_sorted_newest_first(admin_client):
    add_test_incident('LOW',      'Old incident', 'OLD-001')
    add_test_incident('CRITICAL', 'New incident', 'NEW-001')
    response = admin_client.get('/api/incidents')
    data = response.get_json()
    assert data['incidents'][0]['jira_ticket'] == 'NEW-001'
    print("PASS: Incidents sorted newest first")

# ── API: Search & Filter ──────────────────────────────────────────────────────
def test_filter_by_severity(admin_client):
    add_test_incident('CRITICAL', 'Critical issue', 'C-001')
    add_test_incident('LOW',      'Low issue',      'L-001')
    response = admin_client.get('/api/incidents?severity=CRITICAL')
    data = response.get_json()
    assert len(data['incidents']) == 1
    assert data['incidents'][0]['severity'] == 'CRITICAL'
    print("PASS: Severity filter works correctly")

def test_search_by_root_cause(admin_client):
    add_test_incident('HIGH', 'CPU spike detected', 'C-001')
    add_test_incident('HIGH', 'Memory leak in app', 'M-001')
    response = admin_client.get('/api/incidents?search=CPU')
    data = response.get_json()
    assert len(data['incidents']) == 1
    assert 'CPU' in data['incidents'][0]['root_cause']
    print("PASS: Root cause search works correctly")

def test_search_by_service_name(admin_client):
    add_test_incident('HIGH', 'Issue', 'S-001', 'web-server')
    add_test_incident('HIGH', 'Issue', 'S-002', 'database')
    response = admin_client.get('/api/incidents?search=web-server')
    data = response.get_json()
    assert len(data['incidents']) == 1
    print("PASS: Service name search works correctly")

def test_filter_returns_correct_total(admin_client):
    add_test_incident('CRITICAL', 'Critical issue', 'C-001')
    add_test_incident('LOW',      'Low issue',      'L-001')
    add_test_incident('LOW',      'Low issue 2',    'L-002')
    response = admin_client.get('/api/incidents?severity=LOW')
    data = response.get_json()
    assert data['total'] == 3
    assert len(data['incidents']) == 2
    print("PASS: Total count is correct with filters")

# ── API: CSV Export ───────────────────────────────────────────────────────────
def test_csv_export_returns_file(admin_client):
    add_test_incident('HIGH', 'Test incident', 'TEST-001')
    response = admin_client.get('/api/export-csv')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type
    print("PASS: CSV export returns file correctly")

def test_csv_export_contains_headers(admin_client):
    response = admin_client.get('/api/export-csv')
    data = response.data.decode('utf-8')
    assert 'Root Cause'   in data
    assert 'Severity'     in data
    assert 'Jira Ticket'  in data
    assert 'Triggered By' in data
    print("PASS: CSV contains correct headers")

def test_csv_export_contains_incidents(admin_client):
    add_test_incident('CRITICAL', 'CPU spike in production', 'KAN-999')
    response = admin_client.get('/api/export-csv')
    data = response.data.decode('utf-8')
    assert 'CPU spike in production' in data
    assert 'KAN-999' in data
    print("PASS: CSV contains incident data")

def test_csv_export_empty_database(admin_client):
    response = admin_client.get('/api/export-csv')
    assert response.status_code == 200
    data = response.data.decode('utf-8')
    assert 'ID' in data
    print("PASS: CSV export works with empty database")

# ── API: Status ───────────────────────────────────────────────────────────────
def test_status_endpoint(admin_client):
    response = admin_client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'running'
    assert data['agents'] == 5
    assert 'incidents'    in data
    assert 'last_check'   in data
    print("PASS: Status endpoint returns correct data")

def test_status_incident_count(admin_client):
    add_test_incident('HIGH', 'Test', 'T-001')
    add_test_incident('LOW',  'Test', 'T-002')
    response = admin_client.get('/api/status')
    data = response.get_json()
    assert data['incidents'] == 2
    print("PASS: Status incident count is correct")

# ── API: CPU History ──────────────────────────────────────────────────────────
def test_cpu_history_endpoint(admin_client):
    response = admin_client.get('/api/cpu-history')
    assert response.status_code == 200
    data = response.get_json()
    assert 'labels' in data
    assert 'values' in data
    assert len(data['labels']) == len(data['values'])
    print("PASS: CPU history endpoint returns correct structure")

# ── API: Severity Counts ──────────────────────────────────────────────────────
def test_severity_counts_endpoint(admin_client):
    add_test_incident('CRITICAL', 'Test', 'C-001')
    add_test_incident('CRITICAL', 'Test', 'C-002')
    add_test_incident('HIGH',     'Test', 'H-001')
    response = admin_client.get('/api/severity-counts')
    assert response.status_code == 200
    data = response.get_json()
    assert data['CRITICAL'] == 2
    assert data['HIGH']     == 1
    assert data['MEDIUM']   == 0
    assert data['LOW']      == 0
    print("PASS: Severity counts are correct")

# ── Viewer Access Tests ───────────────────────────────────────────────────────
def test_viewer_can_see_incidents(viewer_client):
    response = viewer_client.get('/api/incidents')
    assert response.status_code == 200
    print("PASS: Viewer can read incidents")

def test_viewer_cannot_run_pipeline(viewer_client):
    response = viewer_client.post('/api/run-pipeline')
    assert response.status_code == 403
    print("PASS: Viewer blocked from pipeline")

def test_viewer_can_export_csv(viewer_client):
    response = viewer_client.get('/api/export-csv')
    assert response.status_code == 200
    print("PASS: Viewer can export CSV")