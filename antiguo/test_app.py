import pytest
from app import app, tasks

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def clear_tasks():
    tasks.clear()
    yield
    tasks.clear()

def test_home(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.decode() == 'To-do app is running'

def test_get_tasks(client):
    response = client.get('/tasks')
    assert response.status_code == 200
    assert response.get_json() == {"tasks": []}

def test_add_task(client):
    response = client.post('/tasks', json={"task": "New task"})
    assert response.status_code == 201
    data = response.get_json()
    assert data['task'] == "New task"
    assert data['id'] == 1
    
    # Verify it's in the list
    response = client.get('/tasks')
    assert response.get_json() == {"tasks": [{"id": 1, "task": "New task"}]}

def test_delete_task(client):
    # Add a task first
    client.post('/tasks', json={"task": "Task to delete"})
    
    # Delete it
    response = client.delete('/tasks/1')
    assert response.status_code == 200
    assert response.get_json() == {"message": "Task deleted"}
    
    # Verify it's gone
    response = client.get('/tasks')
    assert response.get_json() == {"tasks": []}

def test_delete_nonexistent_task(client):
    response = client.delete('/tasks/999')
    assert response.status_code == 404
    assert response.get_json() == {"error": "Task not found"}

