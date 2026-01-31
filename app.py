from flask import Flask, render_template
from flask_login import LoginManager
from flask_mail import Mail
from backend.routes.auth import auth_bp
from backend.routes.compliance import comp_bp
from backend.routes.dashboard import dash_bp
from backend.utils.billing import billing_bp
from backend.database.database import db
from backend.models.auth import User
from backend.models.compliance import ComplianceRequirement, ComplianceDocument
from backend.models.reminders import ReminderLog
from backend.models.finance import Subscription
from backend.utils.scheduler import start_scheduler
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clearcomply.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@clearcomply.com')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dash_bp, url_prefix='/dashboard')
app.register_blueprint(comp_bp, url_prefix='/compliance')
app.register_blueprint(billing_bp, url_prefix='/billing')

@app.route('/')
def landing_page():
    return render_template('landing_page.html')

# Create tables and start scheduler
with app.app_context():
    db.create_all()
    start_scheduler(app, mail)

if __name__ == '__main__':
    app.run(debug=True)