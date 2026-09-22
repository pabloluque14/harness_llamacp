import pytest
import app
from app import app, tasks

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        tasks.clear()
        app.task_id_counter = 1
        yield client

def test_get_tasks_empty(client):
    """Verify it returns an empty list initially."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.get_json() == []

def test_add_task(client):
    """Verify it adds a task and returns the correct JSON."""
    response = client.post('/add', json={'task': 'Test task'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] == 1
    assert data['task'] == 'Test task'

def test_get_tasks_after_add(client):
    """Verify it returns the added task."""
    client.post('/add', json={'task': 'Test task'})
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['task'] == 'Test task'
    assert data[0]['id'] == 1

def test_delete_task_success(client):
    """Verify it deletes the task and returns success."""
    client.post('/add', json={'task': 'Task to delete'})
    # The task ID should be 1
    response = client.delete('/delete/1')
    assert response.status_code == 200
    assert "deleted successfully" in response.get_json()['message']
    
    # Verify it's gone
    get_response = client.get('/')
    assert get_response.get_json() == []

def test_delete_task_not_found(client):
    """Verify it returns 404 for a non-existent ID."""
    response = client.delete('/delete/999')
    assert response.status_code == 404
    assert "not found" in response.get_json()['error']
