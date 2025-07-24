from flask import Flask, render_template, redirect, url_for, request, session, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, UserMixin, current_user
)
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -----------------------------
# Models
# -----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    time_spent = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        tasks = Task.query.filter_by(user_id=current_user.id).all()
        tasks_data = [
            {
                'id': task.id,
                'title': task.title,
                'category': task.category,
                'time_spent': task.time_spent
            } for task in tasks
        ]
        return render_template('index.html', tasks=tasks, tasks_data=tasks_data)
    else:
        return render_template('index.html', tasks=[], tasks_data=[])


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    tasks_data = [
        {
            'id': task.id,
            'title': task.title,
            'category': task.category,
            'time_spent': task.time_spent
        } for task in tasks
    ]
    return render_template('dashboard.html', tasks=tasks, tasks_data=tasks_data)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    category = request.form.get('category', '')
    new_task = Task(title=title, category=category, user_id=current_user.id)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/download_csv')
@login_required
def download_csv():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['ID', 'Title', 'Category', 'Time Spent (minutes)'])
    for task in tasks:
        writer.writerow([task.id, task.title, task.category, task.time_spent])
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=task_report.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/update_time/<int:task_id>', methods=['POST'])
@login_required
def update_time(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return "Unauthorized", 403
    task.time_spent = int(request.form.get('time_spent', 0))
    db.session.commit()
    return 'OK', 200

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
