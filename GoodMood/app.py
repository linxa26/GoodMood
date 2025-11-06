from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os, datetime, calendar
from datetime import date
import json
from flask import send_file, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'my_super_secret_key'

DB_PATH = os.path.join(os.path.dirname(__file__), 'moodpress.db')

MOODS = {
    "happy": {"emoji": "😊", "title": "Радостно", "color": "#FFC857"},
    "calm": {"emoji": "😌", "title": "Спокойно", "color": "#7CD992"},
    "sad": {"emoji": "😔", "title": "Грустно", "color": "#6C8AE4"},
    "anxious": {"emoji": "😟", "title": "Тревожно", "color": "#B57EDC"},
    "hard": {"emoji": "😤", "title": "Тяжело", "color": "#F28C28"},
}

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS moods (
            date TEXT,
            mood TEXT,
            note TEXT,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (date, user_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            count INTEGER NOT NULL,
            user_id INTEGER NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS sleep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            user_id INTEGER NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password_raw = request.form.get('password', '')

        if not name or not email or not password_raw:
            flash('Заполни все поля', 'error')
            return render_template('login.html')  # или register.html, как у тебя

        password = generate_password_hash(password_raw)

        with sqlite3.connect(DB_PATH) as conn:
            try:
                conn.execute(
                    'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                    (name, email, password)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                flash('Email уже используется', 'error')
                return redirect(url_for('register'))

        flash('Успешная регистрация! Теперь войди.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute(
                'SELECT id, name, password FROM users WHERE email = ?',
                (email,)
            ).fetchone()

        # Диагностика в консоли
        print("🧩 Проверяем вход:", user, "raw_password=", repr(password))

        if user and check_password_hash(user[2], password):
            session.clear()  # важно!
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            print("✅ Вход ОК, session =", dict(session))
            return redirect(url_for('index'))

        flash('Неверный email или пароль', 'error')
        print("❌ Ошибка входа")
        # Остаёмся на странице логина, чтобы не ловить цикл редиректов
        return render_template('login.html', email=email)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        mood = request.form.get('mood')
        note = request.form.get('note', '')
        today = datetime.date.today().isoformat()

        conn = sqlite3.connect(DB_PATH)
        conn.execute('REPLACE INTO moods (date, mood, note, user_id) VALUES (?, ?, ?, ?)',
                     (today, mood, note, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT mood, note FROM moods WHERE date=? AND user_id=?', (today, user_id)).fetchone()
    conn.close()

    saved_mood = row[0] if row else None
    return render_template('index.html', moods=MOODS, saved_mood=saved_mood, page_class="cowboy")


@app.route('/calendar/', methods=['GET', 'POST'])
@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
def show_calendar(year=None, month=None):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    if request.method == 'POST':
        chosen_date = request.form.get('date')
        mood = request.form.get('mood')
        note = request.form.get('note', '')
        if chosen_date and mood:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('REPLACE INTO moods (date, mood, note, user_id) VALUES (?, ?, ?, ?)',
                         (chosen_date, mood, note, user_id))
            conn.commit()
            conn.close()

    conn = sqlite3.connect(DB_PATH)
    moods = dict(conn.execute('SELECT date, mood FROM moods WHERE user_id=?', (user_id,)).fetchall())
    conn.close()

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.itermonthdates(year, month)

    days = []
    for day in month_days:
        if day.month == month:
            day_str = day.isoformat()
            mood_key = moods.get(day_str)
            color = MOODS[mood_key]["color"] if mood_key in MOODS else "#f0f0f0"
            emoji = MOODS[mood_key]["emoji"] if mood_key in MOODS else ""
            days.append({"date": day.day, "full": day_str, "color": color, "emoji": emoji})
        else:
            days.append({"date": "", "full": "", "color": "transparent", "emoji": ""})

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    month_name = MONTHS_RU[month]

    return render_template('calendar.html', days=days, month=month, year=year,
                           month_name=month_name, moods=MOODS,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           page_class="calendar")


@app.route('/steps', methods=['GET', 'POST'])
def steps():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date']
        count = request.form['count']
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('REPLACE INTO steps (date, count, user_id) VALUES (?, ?, ?)', (date, count, user_id))

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute('SELECT date, count FROM steps WHERE user_id=? ORDER BY date DESC', (user_id,)).fetchall()

    # 👇 фон как на главной
    return render_template('steps.html', rows=rows, page_class="cowboy")




@app.route('/sleep', methods=['GET', 'POST'])
def sleep():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date']
        hours = request.form['hours']
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('REPLACE INTO sleep (date, hours, user_id) VALUES (?, ?, ?)', (date, hours, user_id))

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute('SELECT date, hours FROM sleep WHERE user_id=? ORDER BY date DESC', (user_id,)).fetchall()

    # 👇 фон как на главной
    return render_template('sleep.html', rows=rows, page_class="cowboy")


@app.route('/mood_trend')
def mood_trend():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_PATH) as conn:
        moods_data = conn.execute('SELECT date, mood FROM moods WHERE user_id=? ORDER BY date', (user_id,)).fetchall()
        steps_data = dict(conn.execute('SELECT date, count FROM steps WHERE user_id=?', (user_id,)).fetchall())
        sleep_data = dict(conn.execute('SELECT date, hours FROM sleep WHERE user_id=?', (user_id,)).fetchall())

    labels = []
    mood_values = []
    step_values = []
    sleep_values = []

    for date_str, mood in moods_data:
        labels.append(date_str)
        mood_values.append(MOODS[mood]["title"])
        step_values.append(steps_data.get(date_str, 0))
        sleep_values.append(sleep_data.get(date_str, 0))

    return render_template('mood_trend.html',
                           labels=json.dumps(labels),
                           mood_values=json.dumps(mood_values),
                           step_values=json.dumps(step_values),
                           sleep_values=json.dumps(sleep_values))


@app.route('/export')
def export_data():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT date, mood, note FROM moods WHERE user_id=?', (user_id,)).fetchall()
    conn.close()

    data = [{"date": r[0], "mood": r[1], "note": r[2]} for r in rows]
    export_path = os.path.join(os.path.dirname(__file__), 'moodpress_export.json')
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return send_file(export_path, as_attachment=True)


@app.route('/import', methods=['POST'])
def import_data():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    file = request.files.get('file')
    if not file:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    data = json.load(file)
    conn = sqlite3.connect(DB_PATH)
    for entry in data:
        conn.execute('REPLACE INTO moods (date, mood, note, user_id) VALUES (?, ?, ?, ?)',
                     (entry['date'], entry['mood'], entry.get('note', ''), user_id))
    conn.commit()
    conn.close()

    flash('Данные успешно импортированы!', 'success')
    return redirect(url_for('index'))


@app.route('/stats')
def stats():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    year = request.args.get('year', datetime.date.today().year, type=int)
    month = request.args.get('month', datetime.date.today().month, type=int)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT mood, COUNT(*) 
            FROM moods 
            WHERE user_id = ? 
              AND strftime('%Y', date) = ? 
              AND strftime('%m', date) = ?
            GROUP BY mood
        """, (user_id, str(year), f"{month:02d}")).fetchall()

    labels = [MOODS[m]["title"] if m in MOODS else m for m, _ in rows]
    values = [count for _, count in rows]
    colors = [MOODS[m]["color"] if m in MOODS else "#CCCCCC" for m, _ in rows]

    month_name = MONTHS_RU[month]

    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year if month > 1 else year - 1
    next_year = year if month < 12 else year + 1

    # ✅ Фон для страницы статистики
    return render_template(
        'stats.html',
        labels=labels,
        values=values,
        colors=colors,
        month_name=month_name,
        year=year,
        prev_month=prev_month,
        next_month=next_month,
        prev_year=prev_year,
        next_year=next_year,
        page_class="stats"
    )


if __name__ == '__main__':
    init_db()  # создаёт БД, если нет
    app.run(debug=True)
