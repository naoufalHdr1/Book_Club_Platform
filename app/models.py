from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.types import PickleType
from sqlalchemy.ext.mutable import MutableList

# Association table for events and users
event_participants = db.Table('event_participants',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), default="https://t4.ftcdn.net/jpg/00/64/67/27/360_F_64672736_U5kpdGs9keUll8CRQ3p3YaEv2M6qkVY5.jpg", nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Bookshelves
    bookshelves = db.relationship('Bookshelf', backref='owner', lazy=True, cascade="all, delete-orphan")
    favorite_books = db.Column(MutableList.as_mutable(PickleType), default=[])

    def create_default_bookshelves(self):
        # Define the default bookshelf names and corresponding descriptions
        default_bookshelves = [
            {'name': 'Want to Read', 'description': 'Books you plan to read in the future.'},
            {'name': 'Currently Reading', 'description': 'Books you are currently reading.'},
            {'name': 'Read', 'description': 'Books you have already read.'}
        ]

        # Loop through each default bookshelf and create it with the description
        for bookshelf_data in default_bookshelves:
            bookshelf = Bookshelf(name=bookshelf_data['name'],
                                  description=bookshelf_data['description'],
                                  user_id=self.id)
            db.session.add(bookshelf)

        db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bookshelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Many-to-Many Relationship with Books
    books = db.Column(MutableList.as_mutable(PickleType), default=[])

    def __repr__(self):
        return f'<Bookshelf {self.name}>'

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.String(30), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=True)
    genre = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(255), nullable=True)
    __table_args__ = (db.UniqueConstraint('year', 'month', 'title', name='unique_book_per_month'),)

class BookshelfBook(db.Model):
    __tablename__ = 'bookshelf_book'
    bookshelf_id = db.Column(db.Integer, db.ForeignKey('bookshelf.id'), primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), primary_key=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

    user = db.relationship('User', backref='reviews')

class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    club_img = db.Column(db.String(200), default="https://www.lismore.nsw.gov.au/files/assets/public/v/2/2.-community/2.-events-amp-venues/events/2023/libraries/book-club-image.jpg", nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Tracks which user created the club

    # Relationships
    memberships = db.relationship('Membership', backref='club', lazy=True)
    creator = db.relationship('User', backref='clubs_created')

class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # Roles: 'admin', 'moderator', 'member'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to the User
    user = db.relationship('User', backref='memberships')

    # Unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint('user_id', 'club_id', name='_user_club_uc'),)

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    club = db.relationship('Club', backref='discussions')
    creator = db.relationship('User', backref='discussions')
    comments = db.relationship('Comment', backref='discussion', lazy=True, cascade="all, delete-orphan")

class EventDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    event = db.relationship('Event', backref='event_discussions')
    creator = db.relationship('User', backref='event_discussions')
    comments = db.relationship('Comment', backref='event_discussion', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=True)  # For club discussions
    event_discussion_id = db.Column(db.Integer, db.ForeignKey('event_discussion.id'), nullable=True)  # For event discussions
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    creator = db.relationship('User', backref='comments')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    club = db.relationship('Club', backref='events')
    user = db.relationship('User', backref='events')
    participants = db.relationship('User', secondary=event_participants, backref='participated_events', lazy='dynamic')
