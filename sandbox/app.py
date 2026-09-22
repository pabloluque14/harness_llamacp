from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage for tasks
tasks = []
# Counter to assign unique IDs to tasks
task_id_counter = 1

@app.route('/', methods=['GET'])
def get_tasks():
    """List all tasks."""
    return jsonify(tasks), 200

@app.route('/add', methods=['POST'])
def add_task():
    global task_id_counter
    """Add a new task."""
    data = request.get_json()

    if not data or 'task' not in data:
        return jsonify({"error": "Missing 'task' field in request body"}), 400
    
    new_task = {
        "id": task_id_counter,
        "task": data['task']
    }
    tasks.append(new_task)
    task_id_counter += 1
    
    return jsonify(new_task), 201

@app.route('/delete/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task by its ID."""
    global tasks
    task_to_delete = next((task for task in tasks if task['id'] == task_id), None)
    
    if task_to_delete is None:
        return jsonify({"error": f"Task with ID {task_id} not found"}), 404
    
    tasks = [task for task in tasks if task['id'] != task_id]
    return jsonify({"message": f"Task {task_id} deleted successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
