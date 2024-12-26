import pytest
from app import app
from flask import session
from unittest.mock import patch
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Please allow location access to view weather information.' in response.data

@patch('app.requests.get')
def test_get_weather_success(mock_get, client):
    # Generate mock 'list' data for 4 days, at 12 PM each day
    base_dt = int(datetime.now().timestamp())
    list_data = []
    for i in range(1, 17):  # 16 entries, every 3 hours for 2 days
        list_data.append({
            'dt': base_dt + i * 10800,  # 3 hours in seconds
            'weather': [{'icon': '01d', 'description': 'clear sky'}],
            'main': {'temp': 25 + i, 'feels_like': 27 + i}
        })

    mock_response = {
        'list': list_data,
        'city': {
            'name': 'Test City',
            'sunrise': base_dt - 3600,
            'sunset': base_dt + 36000
        }
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response

    response = client.post('/weather', data={'latitude': '10', 'longitude': '20'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test City' in response.data
    assert b'clear sky' in response.data
    assert b'25' in response.data  # Example temperature

    # Verify session data
    with client.session_transaction() as sess:
        assert 'weather' in sess
        assert 'forecast' in sess
        assert sess['weather']['location'] == 'Test City'
        assert len(sess['forecast']) == 4

@patch('app.requests.get')
def test_get_weather_failure(mock_get, client):
    mock_get.return_value.status_code = 404
    response = client.post('/weather', data={'latitude': '10', 'longitude': '20'})
    assert response.status_code == 200
    assert b'Failed to fetch weather data.' in response.data

def test_weather_result_no_session(client):
    response = client.get('/weather_result', follow_redirects=True)
    assert response.status_code == 200
    assert b'Please allow location access to view weather information.' in response.data