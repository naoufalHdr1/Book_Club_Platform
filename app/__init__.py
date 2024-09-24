# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import atexit

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'

# Initialize scheduler
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'
    app.config.from_object('app.config.Config')
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Initialize the scheduler
    executors = {
        'default': ThreadPoolExecutor(10)
    }
    scheduler = BackgroundScheduler(executors=executors)

    from app.routes import scrape_books
    def run_scrape_books():
        with app.app_context():
            scrape_books()

    # Call the scraping function immediately after the app is created
    """
    with app.app_context():
        scrape_books()
    """

    # Here, pass the function reference (without parentheses) to `add_job`
    scheduler.add_job(func=run_scrape_books, trigger="interval", weeks=1)

    # Start the scheduler
    scheduler.start()

    # Register shutdown hook to stop scheduler
    atexit.register(lambda: scheduler.shutdown())

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from app.routes import main, club_bp
    app.register_blueprint(main)
    app.register_blueprint(club_bp)

    # Register custom template filter here
    @app.template_filter('find_bookshelf')
    def find_bookshelf(book_id, bookshelves):
        for bookshelf in bookshelves:
            if book_id in bookshelf.books:
                return bookshelf.name
        return None
    
    return app
