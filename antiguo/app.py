from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory list to store tasks
tasks = []

@app.route('/', methods=['GET'])
def home():
    return "To-do app is running"

@app.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify({"tasks": tasks}), 200

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    if not data or 'task' not in data:
        return jsonify({"error": "Missing task description"}), 400
    
    new_task = {"id": len(tasks) + 1, "task": data['task']}
    tasks.append(new_task)
    return jsonify(new_task), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    
    tasks = [t for t in tasks if t['id'] != task_id]
    return jsonify({"message": "Task deleted"}), 200

if __name__ == "__main__":
    app.run(debug=True)
