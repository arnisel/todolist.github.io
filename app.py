from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='templates')


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


@app.route('/')
def index():
    # derive simple stats from TASKS
    today_tasks = sum(1 for t in TASKS if t.get('status') == 'todo')
    this_week = sum(1 for t in TASKS if t.get('status') == 'done')
    upcoming = sum(1 for t in TASKS if t.get('status') == 'in_progress')
    data = {
        'user_name': 'Arnis',
        'today_tasks': today_tasks,
        'this_week': this_week,
        'upcoming': upcoming
    }
    return render_template('index.html', **data)


@app.route('/tasks')
def tasks():
    return render_template('tasks.html', user_name='Arnis', tasks=TASKS)


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
    # placeholder projects view
    return render_template('projects.html', user_name='Arnis')


@app.route('/reports')
def reports():
    # placeholder reports view
    return render_template('reports.html', user_name='Arnis')


@app.route('/calendar')
def calendar():
    # simple placeholder calendar page
    return render_template('calendar.html', user_name='Arnis')


if __name__ == '__main__':
    # debug=True is convenient for local development; remove or set False for production
    app.run(host='127.0.0.1', port=5000, debug=True)
