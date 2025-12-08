from datetime import datetime
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')


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
    # projects table to persist project metadata
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    # users table for authentication
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()
    # Add completed_at column if it doesn't exist (safe on repeated runs)
    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
        conn.commit()
    except Exception:
        # column already exists or other issue; ignore
        pass
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

# Projects are persisted in the `projects` table in SQLite (see init_db)


def load_all_tasks():
    """Load all tasks from the DB and return a list of dicts (same shape as older TASKS)."""
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
            'status': r['status'] or 'todo',
            'completed_at': r['completed_at'] or ''
        })
    conn.close()
    return tasks


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
        'user_name': session.get('user', 'Arnis'),
        'today_tasks': today_tasks,
        'this_week': this_week,
        'upcoming': upcoming
    }
    return render_template('index.html', **data)


@app.route('/tasks')
def tasks():
    tasks = load_all_tasks()
    return render_template('tasks.html', user_name=session.get('user', 'Arnis'), tasks=tasks)


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

    # if the form included a `next` target (for returning to calendar), redirect there
    next_target = request.form.get('next') or request.args.get('next')
    if next_target:
        return redirect(next_target)
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
    # set or clear completed_at when status changes
    if new_status == 'done':
        completed_at = datetime.utcnow().date().isoformat()
        cur.execute('UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?', (new_status, completed_at, int(tid)))
    else:
        cur.execute('UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?', (new_status, int(tid)))
    conn.commit()
    conn.close()
    return jsonify({'id': int(tid), 'status': new_status})


@app.route('/projects')
def projects():
    # aggregate DB tasks into projects summary
    from collections import defaultdict

    tasks = load_all_tasks()
    proj_map = defaultdict(lambda: {'task_count': 0, 'completed': 0})
    for t in tasks:
        name = t.get('project') or 'Genel'
        proj_map[name]['task_count'] += 1
        if t.get('status') == 'done':
            proj_map[name]['completed'] += 1

    # load stored projects from DB (so projects with zero tasks are included)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, description FROM projects ORDER BY name COLLATE NOCASE')
    stored = cur.fetchall()
    conn.close()

    projects_list = []
    seen = set()

    # first, include projects that have tasks (from task aggregation)
    for name, data in proj_map.items():
        total = data['task_count']
        done = data['completed']
        percent = int(round((done / total) * 100)) if total else 0
        projects_list.append({
            'name': name,
            'task_count': total,
            'completed': done,
            'percent': percent,
            'percent_style': f"width: {percent}%"
        })
        seen.add(name)

    # then add stored projects that had no tasks yet
    for r in stored:
        pname = r['name']
        if pname in seen:
            continue
        projects_list.append({
            'id': r['id'],
            'name': pname,
            'task_count': 0,
            'completed': 0,
            'percent': 0,
            'percent_style': 'width: 0'
        })

    projects_list = sorted(projects_list, key=lambda p: p['name'].lower())
    return render_template('projects.html', user_name=session.get('user', 'Arnis'), projects=projects_list)


@app.route('/add_project', methods=['POST'])
def add_project():
    # Persist project in SQLite
    name = request.form.get('name')
    description = request.form.get('description') or ''
    if name:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT OR IGNORE INTO projects (name, description) VALUES (?, ?)', (name, description))
            conn.commit()
        finally:
            conn.close()
    return redirect(url_for('projects'))


@app.route('/delete_task', methods=['POST'])
def delete_task():
    data = request.get_json() or {}
    tid = data.get('id') or request.form.get('id')
    if not tid:
        return jsonify({'error': 'missing id'}), 400
    try:
        tid = int(tid)
    except Exception:
        return jsonify({'error': 'invalid id'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id = ?', (tid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'id': tid})


@app.route('/delete_project', methods=['POST'])
def delete_project():
    data = request.get_json() or {}
    pid = data.get('id')
    name = data.get('name') or request.form.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if pid:
            try:
                pid = int(pid)
            except Exception:
                return jsonify({'error': 'invalid id'}), 400
            # get name for cascade deletion of tasks
            cur.execute('SELECT name FROM projects WHERE id = ?', (pid,))
            row = cur.fetchone()
            if row:
                pname = row['name']
                cur.execute('DELETE FROM projects WHERE id = ?', (pid,))
                cur.execute('DELETE FROM tasks WHERE project = ?', (pname,))
                conn.commit()
                return jsonify({'ok': True, 'id': pid, 'name': pname})
            else:
                return jsonify({'error': 'not found'}), 404
        elif name:
            # delete tasks with this project name and any project record
            cur.execute('DELETE FROM projects WHERE name = ?', (name,))
            cur.execute('DELETE FROM tasks WHERE project = ?', (name,))
            conn.commit()
            return jsonify({'ok': True, 'name': name})
        else:
            return jsonify({'error': 'missing id or name'}), 400
    finally:
        conn.close()


@app.route('/reports')
def reports():
    # derive stats and chart data from DB tasks
    from datetime import date, timedelta
    tasks = load_all_tasks()

    # Basic stats (existing)
    today_tasks = sum(1 for t in tasks if t.get('status') == 'todo')
    this_week = sum(1 for t in tasks if t.get('status') == 'done')
    upcoming = sum(1 for t in tasks if t.get('status') == 'in_progress')

    # Prepare daily data for the last 7 days (counts of done tasks whose due_sort == that date)
    today = date.today()
    last7 = [today - timedelta(days=i) for i in range(6, -1, -1)]  # oldest -> newest
    daily_labels = []
    daily_values = []
    for d in last7:
        daily_labels.append(d.strftime('%a'))  # short weekday
        iso = d.isoformat()
        cnt = 0
        for t in tasks:
            completed = t.get('completed_at')
            if not completed:
                continue
            try:
                if completed == iso:
                    cnt += 1
            except Exception:
                continue
        daily_values.append(cnt)

    # Prepare weekly data for the last 4 weeks (counts of done tasks whose due_sort in that week)
    # Find start of current week (Monday)
    current_week_start = today - timedelta(days=today.weekday())
    weekly_labels = []
    weekly_values = []
    for i in range(4):
        start = current_week_start - timedelta(weeks=(3 - i))
        end = start + timedelta(days=6)
        label = f"{start.day}.{start.month}"
        weekly_labels.append(label)
        cnt = 0
        for t in tasks:
            ds = t.get('completed_at')
            if not ds:
                continue
            try:
                ds_date = datetime.strptime(ds, '%Y-%m-%d').date()
            except Exception:
                continue
            if start <= ds_date <= end:
                cnt += 1
        weekly_values.append(cnt)

    # Project-based completed counts for doughnut chart
    from collections import defaultdict
    proj_map = defaultdict(lambda: {'total': 0, 'done': 0})
    for t in tasks:
        name = t.get('project') or 'Genel'
        proj_map[name]['total'] += 1
        if t.get('status') == 'done':
            proj_map[name]['done'] += 1

    project_labels = []
    project_values = []
    for pname, pdata in proj_map.items():
        project_labels.append(pname)
        project_values.append(pdata['done'])

    # Fallbacks handled in template via default; pass Python lists to template (serializable)
    return render_template(
        'reports.html',
        user_name=session.get('user', 'Arnis'),
        today_tasks=today_tasks,
        this_week=this_week,
        upcoming=upcoming,
        daily_labels=daily_labels,
        daily_values=daily_values,
        weekly_labels=weekly_labels,
        weekly_values=weekly_values,
        project_labels=project_labels,
        project_values=project_values
    )


@app.route('/calendar')
def calendar():
    # build a month calendar and map DB tasks to dates (uses tasks[*]['due_sort'] if present)
    import calendar as _calendar

    # allow navigation via query params
    try:
        year = int(request.args.get('year', ''))
        month = int(request.args.get('month', ''))
    except Exception:
        today = datetime.utcnow().date()
        year = today.year
        month = today.month

    if not (1 <= month <= 12):
        today = datetime.utcnow().date()
        year = today.year
        month = today.month

    cal = _calendar.Calendar(firstweekday=0)
    month_weeks = cal.monthdatescalendar(year, month)

    # Build serializable structure for template
    calendar_weeks = []
    for week in month_weeks:
        w = []
        for d in week:
            w.append({'day': d.day, 'iso': d.isoformat(), 'in_month': (d.month == month)})
        calendar_weeks.append(w)

    # map events by iso date from DB
    events = {}
    for t in load_all_tasks():
        ds = t.get('due_sort')
        if ds:
            events.setdefault(ds, []).append({'id': t.get('id'), 'title': t.get('title'), 'project': t.get('project'), 'status': t.get('status')})

    # compute prev/next month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    turkish_months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    month_title = f"{turkish_months[month-1]} {year}"

    return render_template('calendar.html', user_name=session.get('user', 'Arnis'), calendar_weeks=calendar_weeks, events=events, month_title=month_title, prev_year=prev_year, prev_month=prev_month, next_year=next_year, next_month=next_month)


@app.route('/api/upcoming')
def api_upcoming():
    """Return JSON list of tasks due tomorrow (1 day left) and not completed."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Select tasks with due_sort equal to tomorrow's date and not done
        cur.execute("SELECT * FROM tasks WHERE due_sort IS NOT NULL AND due_sort <> '' AND DATE(due_sort) = DATE('now','+1 day') AND status != 'done'")
        rows = cur.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                'id': r['id'],
                'project': r['project'],
                'title': r['title'],
                'due_sort': r['due_sort'],
                'status': r['status']
            })
        return jsonify({'count': len(tasks), 'tasks': tasks})
    finally:
        conn.close()


@app.before_request
def require_login():
    # Allow unauthenticated access to login, register and static assets
    allowed_endpoints = ('login', 'register', 'static')
    endpoint = request.endpoint
    if endpoint is None or endpoint in allowed_endpoints:
        return
    if not session.get('user'):
        return redirect(url_for('login', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Login using stored users in the database
    if session.get('user'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not email or not password:
            error = 'E-posta ve şifre girin.'
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, password_hash, first_name FROM users WHERE email = ?', (email,))
            row = cur.fetchone()
            conn.close()
            if not row:
                error = 'Kayıt bulunamadı. Lütfen önce kayıt olun.'
            else:
                pw_hash = row['password_hash']
                if check_password_hash(pw_hash, password):
                    # successful login
                    session['user'] = email
                    # optionally store display name
                    try:
                        session['display_name'] = row['first_name'] or email
                    except Exception:
                        session['display_name'] = email
                    next_url = request.args.get('next') or url_for('index')
                    return redirect(next_url)
                else:
                    error = 'E-posta veya şifre hatalı.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        password_confirm = request.form.get('password_confirm') or ''
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        if not email or not password:
            error = 'E-posta ve şifre gereklidir.'
        elif password != password_confirm:
            error = 'Şifreler eşleşmiyor.'
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cur.fetchone():
                # already registered
                conn.close()
                return redirect(url_for('login'))
            pw_hash = generate_password_hash(password)
            cur.execute('INSERT INTO users (email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?)', (email, pw_hash, first_name, last_name))
            conn.commit()
            conn.close()
            session['user'] = email
            session['display_name'] = first_name or email
            return redirect(url_for('index'))

    return render_template('register.html', error=error)


if __name__ == '__main__':
    # ensure DB exists before starting
    init_db()
    app.run(debug=True)

