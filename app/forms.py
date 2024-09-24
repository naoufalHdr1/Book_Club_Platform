from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField,DateTimeField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
from app.models import User

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    submit = SubmitField('Add Book')

class BookshelfForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    submit = SubmitField('Create Bookshelf')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    genre = StringField('Genre', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Submit')

class ReviewForm(FlaskForm):
    content = TextAreaField('Review', validators=[DataRequired()])
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    submit = SubmitField('Submit Review')

class ClubForm(FlaskForm):
    name = StringField('Club Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    profile_picture = StringField('Profile Picture URL')
    category = SelectField('Category', choices=[('books', 'Books'), ('movies', 'Movies'), ('general', 'General')], default='books')
    submit = SubmitField('Create Club')

class DiscussionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Create Discussion')

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    start_time = DateTimeField('Start Time', validators=[DataRequired()], format='%Y-%m-%d')
    end_time = DateTimeField('End Time', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Create Event')

class ProfileForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[DataRequired()])
    profile_picture = StringField('Profile Picture URL')
    submit = SubmitField('Update Profile')
