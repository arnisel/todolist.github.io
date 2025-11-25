from datetime import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')


@app.context_processor
def inject_globals():
    # small global values available in all templates
    return {
        'current_year': datetime.utcnow().year
    }


# In-memory task store for demo purposes (replace with DB for production)
TASKS = [
    {
        'id': 1,
        'project': 'Proje Alfa',
        'title': 'Arayüz Tasarımını Tamamla',
        'description': 'Yeni görev ekleme modal penceresi için arayüz tasarımı yapılacak.',
        'priority': 'high',
        'due': '25 Aralık',
        'due_sort': '2025-12-25',
        'status': 'todo'
    },
    {
        'id': 2,
        'project': 'Proje Beta',
        'title': 'API Entegrasyonu',
        'description': "Kullanıcı verilerini çekmek için backend API'lerini ön yüze entegre et.",
        'priority': 'medium',
        'due': '28 Aralık',
        'due_sort': '2025-12-28',
        'status': 'in_progress'
    },
    {
        'id': 3,
        'project': 'Pazarlama',
        'title': 'Sosyal Medya Paylaşımları',
        'description': 'Yeni yıl kampanyası için sosyal medya içeriklerini hazırla ve planla.',
        'priority': 'low',
        'due': '30 Aralık',
        'due_sort': '2025-12-30',
        'status': 'todo'
    },
    {
        'id': 4,
        'project': 'Proje Alfa',
        'title': 'Kullanıcı Akış Diyagramları',
        'description': "Uygulamanın ana özellikleri için kullanıcı akış diyagramlarını oluştur.",
        'priority': 'medium',
        'due': '15 Aralık',
        'due_sort': '2025-12-15',
        'status': 'done'
    }
]

# In-memory projects list (names). Persistent storage recommended for production.
PROJECTS = []


@app.route('/')
def index():
    # derive simple stats from TASKS
    today_tasks = sum(1 for t in TASKS if t.get('status') == 'todo')
    this_week = sum(1 for t in TASKS if t.get('status') == 'done')
    upcoming = sum(1 for t in TASKS if t.get('status') == 'in_progress')
    data = {
        'user_name': session.get('user', 'Arnis'),
        'today_tasks': today_tasks,
        'this_week': this_week,
        'upcoming': upcoming
    }
    return render_template('index.html', **data)


@app.route('/tasks')
def tasks():
    return render_template('tasks.html', user_name=session.get('user', 'Arnis'), tasks=TASKS)


@app.route('/add_task', methods=['POST'])
def add_task():
    # naive in-memory append; production should validate & persist
    title = request.form.get('title')
    project = request.form.get('project') or 'Genel'
    description = request.form.get('description') or ''
    priority = request.form.get('priority') or 'medium'
    due_sort = request.form.get('due_sort') or ''
    due_display = ''
    if due_sort:
        # simple display transformation YYYY-MM-DD -> DD Mon (Turkish month could be localized)
        try:
            dt = datetime.strptime(due_sort, '%Y-%m-%d')
            due_display = dt.strftime('%d %B')
        except Exception:
            due_display = due_sort
    # assign id
    next_id = max((t.get('id', 0) for t in TASKS), default=0) + 1
    TASKS.append({
        'id': next_id,
        'project': project,
        'title': title,
        'description': description,
        'priority': priority,
        'due': due_display or due_sort,
        'due_sort': due_sort,
        'status': 'todo'
    })
    # if the form included a `next` target (for returning to calendar), redirect there
    next_target = request.form.get('next') or request.args.get('next')
    if next_target:
        return redirect(next_target)
    return redirect(url_for('tasks'))



@app.route('/toggle_task', methods=['POST'])
def toggle_task():
    from flask import jsonify
    data = request.get_json() or {}
    tid = data.get('id')
    if tid is None:
        return jsonify({'error': 'missing id'}), 400
    # find task
    for t in TASKS:
        if t.get('id') == int(tid):
            if t.get('status') == 'done':
                t['status'] = 'todo'
            else:
                t['status'] = 'done'
            return jsonify({'id': t['id'], 'status': t['status']})
    return jsonify({'error': 'not found'}), 404


@app.route('/projects')
def projects():
    # aggregate TASKS into projects summary
    from collections import defaultdict

    proj_map = defaultdict(lambda: {'task_count': 0, 'completed': 0})
    for t in TASKS:
        name = t.get('project') or 'Genel'
        proj_map[name]['task_count'] += 1
        if t.get('status') == 'done':
            proj_map[name]['completed'] += 1

    projects_list = []
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

    # include explicitly created projects (may have zero tasks)
    for pname in PROJECTS:
        if pname not in proj_map:
            projects_list.append({
                'name': pname,
                'task_count': 0,
                'completed': 0,
                'percent': 0,
                'percent_style': 'width: 0'
            })

    # sort projects by name
    projects_list = sorted(projects_list, key=lambda p: p['name'].lower())

    return render_template('projects.html', user_name=session.get('user', 'Arnis'), projects=projects_list)


@app.route('/add_project', methods=['POST'])
def add_project():
    # naive in-memory project creation
    name = request.form.get('name')
    description = request.form.get('description') or ''
    if name:
        # ensure PROJECTS exists and add unique
        try:
            existing = PROJECTS
        except NameError:
            # fallback (shouldn't happen)
            globals()['PROJECTS'] = []
            existing = PROJECTS
        if name not in existing:
            existing.append(name)
    return redirect(url_for('projects'))


@app.route('/reports')
def reports():
    # derive simple stats from TASKS similar to index
    today_tasks = sum(1 for t in TASKS if t.get('status') == 'todo')
    this_week = sum(1 for t in TASKS if t.get('status') == 'done')
    upcoming = sum(1 for t in TASKS if t.get('status') == 'in_progress')
    return render_template('reports.html', user_name=session.get('user', 'Arnis'), today_tasks=today_tasks, this_week=this_week, upcoming=upcoming)


@app.route('/calendar')
def calendar():
    # build a month calendar and map TASKS to dates (uses TASKS[*]['due_sort'] if present)
    import calendar as _calendar
    from datetime import date

    # allow navigation via query params
    try:
        year = int(request.args.get('year', ''))
        month = int(request.args.get('month', ''))
    except Exception:
        today = datetime.utcnow().date()
        year = today.year
        month = today.month

    # if year/month missing or invalid, default to today
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
            w.append({
                'day': d.day,
                'iso': d.isoformat(),
                'in_month': (d.month == month)
            })
        calendar_weeks.append(w)

    # map events by iso date
    events = {}
    for t in TASKS:
        ds = t.get('due_sort')
        if ds:
            events.setdefault(ds, []).append({
                'id': t.get('id'),
                'title': t.get('title'),
                'project': t.get('project'),
                'status': t.get('status')
            })

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


@app.before_request
def require_login():
    # Allow unauthenticated access to login, register and static assets
    allowed_endpoints = ('login', 'register', 'static')
    # if endpoint is None (weird requests) or in allowed, skip
    endpoint = request.endpoint
    if endpoint is None or endpoint in allowed_endpoints:
        return
    if not session.get('user'):
        # preserve next param to redirect after login
        return redirect(url_for('login', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Demo login: set session and redirect to home (or next)
    if session.get('user'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email:
            session['user'] = email
            # redirect to next if provided
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Demo registration: create session user and redirect to index
    if session.get('user'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        # very basic validation
        if email and password and password == password_confirm:
            session['user'] = email
            return redirect(url_for('index'))
        # in case of failure, re-render the form (no flash for simplicity)
        return render_template('register.html')

    return render_template('register.html')


if __name__ == '__main__':
    # debug=True is convenient for local development; remove or set False for production
    app.run(host='127.0.0.1', port=5000, debug=True)
