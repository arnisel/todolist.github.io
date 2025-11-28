from datetime import datetime
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__, template_folder='templates')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            due TEXT,
            due_sort TEXT,
            status TEXT DEFAULT 'todo'
        )
        '''
    )
    conn.commit()
    conn.close()


@app.context_processor
def inject_globals():
    return {'current_year': datetime.utcnow().year}

# Ensure DB exists when the module is imported. Flask's CLI imports the app
# module and may not run module-level __main__ code, so create the DB now.
try:
    init_db()
except Exception:
    pass


@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")
    rows = cur.fetchall()
    stats = {r['status']: r['cnt'] for r in rows}
    today_tasks = stats.get('todo', 0)
    this_week = stats.get('done', 0)
    upcoming = stats.get('in_progress', 0)
    conn.close()
    data = {
        'user_name': 'Arnis',
        'today_tasks': today_tasks,
        'this_week': this_week,
        'upcoming': upcoming
    }
    return render_template('index.html', **data)


@app.route('/tasks')
def tasks():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tasks ORDER BY COALESCE(due_sort, "") ASC, priority DESC')
    rows = cur.fetchall()
    tasks = []
    for r in rows:
        tasks.append({
            'id': r['id'],
            'project': r['project'] or 'Genel',
            'title': r['title'],
            'description': r['description'] or '',
            'priority': r['priority'] or 'medium',
            'due': r['due'] or '',
            'due_sort': r['due_sort'] or '',
            'status': r['status'] or 'todo'
        })
    conn.close()
    return render_template('tasks.html', user_name='Arnis', tasks=tasks)


@app.route('/add_task', methods=['POST'])
def add_task():
    title = request.form.get('title')
    project = request.form.get('project') or 'Genel'
    description = request.form.get('description') or ''
    priority = request.form.get('priority') or 'medium'
    due_sort = request.form.get('due_sort') or ''
    due_display = ''
    if due_sort:
        try:
            dt = datetime.strptime(due_sort, '%Y-%m-%d')
            due_display = dt.strftime('%d %B')
        except Exception:
            due_display = due_sort

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO tasks (project, title, description, priority, due, due_sort, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (project, title, description, priority, due_display or due_sort, due_sort, 'todo')
    )
    conn.commit()
    conn.close()
    return redirect(url_for('tasks'))


@app.route('/toggle_task', methods=['POST'])
def toggle_task():
    data = request.get_json() or {}
    tid = data.get('id')
    if tid is None:
        return jsonify({'error': 'missing id'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT status FROM tasks WHERE id = ?', (int(tid),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    current = row['status']
    new_status = 'todo' if current == 'done' else 'done'
    cur.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, int(tid)))
    conn.commit()
    conn.close()
    return jsonify({'id': int(tid), 'status': new_status})


@app.route('/projects')
def projects():
    return render_template('projects.html', user_name='Arnis')


@app.route('/reports')
def reports():
    return render_template('reports.html', user_name='Arnis')


@app.route('/calendar')
def calendar():
    return render_template('calendar.html', user_name='Arnis')


if __name__ == '__main__':
    # ensure DB exists before starting
    init_db()
    app.run(debug=True)

