from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os, datetime, calendar
from datetime import date
import json
from flask import send_file, flash

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'moodpress.db')

MOODS = {
    "happy": {"emoji": "😊", "title": "Радостно", "color": "#FFC857"},  # жёлтый
    "calm": {"emoji": "😌", "title": "Спокойно", "color": "#7CD992"},  # зелёный
    "sad": {"emoji": "😔", "title": "Грустно", "color": "#6C8AE4"},  # синий
    "anxious": {"emoji": "😟", "title": "Тревожно", "color": "#B57EDC"},  # фиолетовый
    "hard": {"emoji": "😤", "title": "Тяжело", "color": "#F28C28"},
}

MONTHS_RU = [
    "",  # чтобы индекс совпадал с номером месяца
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS moods (
            date TEXT PRIMARY KEY,
            mood TEXT,
            note TEXT
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница — выбор настроения"""
    if request.method == 'POST':
        mood = request.form.get('mood')
        note = request.form.get('note', '')
        today = datetime.date.today().isoformat()

        conn = sqlite3.connect(DB_PATH)
        conn.execute('REPLACE INTO moods (date, mood, note) VALUES (?, ?, ?)', (today, mood, note))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute('SELECT mood, note FROM moods WHERE date=?', (today,)).fetchone()
    conn.close()

    saved_mood = row[0] if row else None
    return render_template('index.html', moods=MOODS, saved_mood=saved_mood, page_class="cowboy")


@app.route('/calendar/')
@app.route('/calendar/<int:year>/<int:month>')
@app.route('/calendar/', methods=['GET', 'POST'])
@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@app.route('/calendar/', methods=['GET', 'POST'])
@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
def show_calendar(year=None, month=None):
    """Календарь с выбором эмоций и локализованным названием месяца"""
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    # --- если пользователь выбрал настроение вручную ---
    if request.method == 'POST':
        chosen_date = request.form.get('date')
        mood = request.form.get('mood')
        note = request.form.get('note', '')

        if chosen_date and mood:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('REPLACE INTO moods (date, mood, note) VALUES (?, ?, ?)',
                         (chosen_date, mood, note))
            conn.commit()
            conn.close()

    # --- загрузка всех дней месяца ---
    conn = sqlite3.connect(DB_PATH)
    moods = dict(conn.execute('SELECT date, mood FROM moods').fetchall())
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


@app.route('/stats')
@app.route('/stats/')
@app.route('/stats/<int:year>/<int:month>')
def stats(year=None, month=None):
    """Статистика по конкретному месяцу"""
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    start = f"{year}-{month:02d}-01"
    end_month = month + 1 if month < 12 else 1
    end_year = year if month < 12 else year + 1
    end = f"{end_year}-{end_month:02d}-01"

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT mood, COUNT(*) FROM moods WHERE date >= ? AND date < ? GROUP BY mood",
        (start, end)
    ).fetchall()
    conn.close()

    data = {mood: count for mood, count in rows}
    labels = [MOODS[m]["title"] for m in data]
    values = [data[m] for m in data]
    colors = [MOODS[m]["color"] for m in data]

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    month_name = MONTHS_RU[month]

    return render_template('stats.html', labels=labels, values=values, colors=colors,
                           month=month, year=year, month_name=month_name,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           page_class="stats")


@app.route('/trend')
def mood_trend():
    """График динамики настроения за последнюю неделю"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT date, mood FROM moods WHERE mood IS NOT NULL ORDER BY date').fetchall()
    conn.close()

    # Если данных нет — вернуть пустую страницу
    if not rows:
        return render_template('trend.html', dates=[], scores=[], page_class="trend")

    # Берём только последние 7 записей
    rows = rows[-7:]

    # Баллы для каждого настроения
    mood_scores = {
        "sad": 1,
        "anxious": 2,
        "hard": 2,
        "calm": 4,
        "happy": 5
    }

    # Безопасное преобразование
    dates, scores = [], []
    for d, m in rows:
        if m in mood_scores:
            dates.append(d)
            scores.append(mood_scores[m])
        else:
            # если настроение не найдено — пропускаем
            continue

    # Если вдруг ничего не осталось
    if not dates:
        return render_template('trend.html', dates=[], scores=[], page_class="trend")

    return render_template('trend.html', dates=dates, scores=scores, page_class="trend")


@app.route('/export')
def export_data():
    """Экспорт данных в JSON"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT date, mood, note FROM moods').fetchall()
    conn.close()

    data = [{"date": r[0], "mood": r[1], "note": r[2]} for r in rows]
    export_path = os.path.join(os.path.dirname(__file__), 'moodpress_export.json')
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return send_file(export_path, as_attachment=True)


@app.route('/import', methods=['POST'])
def import_data():
    """Импорт данных из JSON"""
    file = request.files.get('file')
    if not file:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    data = json.load(file)
    conn = sqlite3.connect(DB_PATH)
    for entry in data:
        conn.execute('REPLACE INTO moods (date, mood, note) VALUES (?, ?, ?)',
                     (entry['date'], entry['mood'], entry.get('note', '')))
    conn.commit()
    conn.close()

    flash('Данные успешно импортированы!', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
