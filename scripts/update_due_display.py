#!/usr/bin/env python3
import sqlite3
from datetime import datetime

months_tr = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']

conn = sqlite3.connect('data.db')
cur = conn.cursor()
cur.execute("SELECT id, due_sort FROM tasks WHERE due_sort IS NOT NULL AND due_sort <> ''")
rows = cur.fetchall()
print(f'Found {len(rows)} rows with due_sort')
for r in rows:
    tid = r[0]
    due_sort = r[1]
    try:
        dt = datetime.strptime(due_sort, '%Y-%m-%d')
        due_display = f"{dt.day} {months_tr[dt.month - 1]}"
        cur.execute('UPDATE tasks SET due = ? WHERE id = ?', (due_display, tid))
        print(f'Updated id={tid}')
    except Exception as e:
        print('skip', tid)

conn.commit()
conn.close()
print('done')
