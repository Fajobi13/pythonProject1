import sqlite3
import jwt
from functools import wraps
from flask import Flask, jsonify, request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Initialize Flask app
app = Flask(__name__)

# Secret key for JWT token encoding/decoding
SECRET_KEY = "your-secret-key"

# Prometheus metrics
REQUEST_COUNTER = Counter('http_requests_total', 'Total number of HTTP requests')
REQUEST_LATENCY = Histogram('http_request_latency_seconds', 'Request latency in seconds')
TASK_COUNTER = Counter('task_created_total', 'Total number of tasks created')

# Initialize the SQLite database (create table if it doesn't exist)
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            due_date TEXT,
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'general'
        )
    ''')
    conn.commit()
    conn.close()

# JWT Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except:
            return jsonify({"message": "Token is invalid"}), 403
        return f(*args, **kwargs)
    return decorated_function

# Endpoint to generate JWT token (dummy login)
@app.route('/api/login', methods=['POST'])
def login():
    token = jwt.encode({"user": "admin"}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    REQUEST_COUNTER.inc()  # Increment request counter for health checks
    return jsonify({"status": "up"}), 200

# Create a new task and store it in the SQLite database
@app.route('/api/tasks', methods=['POST'])
@token_required
def create_task():
    with REQUEST_LATENCY.time():  # Measure request latency
        task_data = request.json
        task_name = task_data['task']
        due_date = task_data.get('due_date', None)
        priority = task_data.get('priority', 'medium')
        category = task_data.get('category', 'general')

        with sqlite3.connect('tasks.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO tasks (task, due_date, priority, category)
                VALUES (?, ?, ?, ?)
            ''', (task_name, due_date, priority, category))
            conn.commit()
            task_id = c.lastrowid

        TASK_COUNTER.inc()  # Increment task counter when a new task is created

        new_task = {
            'id': task_id,
            'task': task_name,
            'due_date': due_date,
            'priority': priority,
            'category': category
        }

        return jsonify(new_task), 201

# Get all tasks from the SQLite database
@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks():
    with REQUEST_LATENCY.time():  # Measure request latency
        with sqlite3.connect('tasks.db') as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM tasks')
            rows = c.fetchall()

            tasks = [{
                'id': row[0],
                'task': row[1],
                'due_date': row[2],
                'priority': row[3],
                'category': row[4]
            } for row in rows]

        return jsonify(tasks), 200

# Delete a task by ID from the SQLite database
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    with REQUEST_LATENCY.time():  # Measure request latency
        with sqlite3.connect('tasks.db') as conn:
            c = conn.cursor()
            c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()

        return jsonify({'message': 'Task deleted'}), 200

# Expose Prometheus metrics at the /metrics endpoint for Prometheus to scrape
@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Initialize the database and start the Flask app
if __name__ == '__main__':
    init_db()  # Initialize the SQLite database
    app.run(host='0.0.0.0', port=4000, debug=True)
