import requests, os, json, bleach
from bs4 import BeautifulSoup
from flask import render_template, redirect, url_for, flash, request, current_app, session, jsonify, abort
from app import db
from app.models import User, Book, Review, Club, Membership, Discussion, Event, Bookshelf
from app.forms import RegistrationForm, LoginForm, BookForm, ReviewForm, ClubForm, DiscussionForm, EventForm, ProfileForm, BookshelfForm
from flask_login import login_user, logout_user, current_user, login_required
from flask import Blueprint
from datetime import datetime
from functools import wraps

main = Blueprint('main', __name__)
club_bp = Blueprint('club_bp', __name__)

# User Authentication System

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('Sorry, You are already a member', 'success')
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Create default bookshelves after user is committed
        user.create_default_bookshelves()

        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in', 'success')
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user)
        flash('You have successfully logged in!', 'success')
        return redirect(url_for('main.view_profile', username=user.username))
    return render_template('login.html', form=form)

@main.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out.', 'success')
    else:
        flash('You are not logged in.', 'danger')
    return redirect(url_for('main.home'))

# Book Management

# 3-Club Creation and Management

# decorator to protect routes that should only be accessible to admins.
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        membership = Membership.query.filter_by(user_id=current_user.id, club_id=kwargs['club_id']).first()
        if membership.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@club_bp.route('/clubs')
@login_required
def view_clubs():
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Number of clubs per page
    pagination = Club.query.paginate(page=page, per_page=per_page, error_out=False)
    clubs = pagination.items
    return render_template('view_clubs.html', clubs=clubs, pagination=pagination)


@main.route('/club/<int:club_id>')
@login_required
def view_club(club_id):
    club = Club.query.get_or_404(club_id)

    # Pagination for events
    events_page = request.args.get('events_page', 1, type=int)
    events_per_page = 3
    events_pagination = Event.query.filter_by(club_id=club_id).paginate(page=events_page, per_page=events_per_page, error_out=False)
    events = events_pagination.items

    # Get total number of events
    total_events = Event.query.filter_by(club_id=club_id).count()

    # Get membership info for the current user
    membership = Membership.query.filter_by(club_id=club_id, user_id=current_user.id).first()
    members = Membership.query.filter_by(club_id=club_id).all()

    now = datetime.utcnow()  # Get current time in UTC

    return render_template('view_club.html', club=club, membership=membership, members=members, events=events, events_pagination=events_pagination, now=now, total_events=total_events, past_books=past_books, current_books=current_books)


@club_bp.route('/create_club', methods=['GET', 'POST'])
@login_required
def create_club():
    form = ClubForm()
    if form.validate_on_submit():
        if not form.profile_picture.data:
            club_img = "https://www.lismore.nsw.gov.au/files/assets/public/v/2/2.-community/2.-events-amp-venues/events/2023/libraries/book-club-image.jpg"
        club = Club(
                name=form.name.data,
                description=form.description.data,
                category=form.category.data,
                created_by=current_user.id,
                club_img=club_img
                )
        db.session.add(club)
        db.session.commit()

        # Add the creator as a member with the role of 'admin'
        membership = Membership(user_id=current_user.id, club_id=club.id, role='admin')
        db.session.add(membership)
        db.session.commit()

        flash(f'Club {form.name.data} has been created!', 'success')
        return redirect(url_for('club_bp.view_clubs'))
    return render_template('create_club.html', form=form)

@main.route('/club/<int:club_id>/join', methods=['POST'])
@login_required
def join_club(club_id):
    club = Club.query.get_or_404(club_id)

    # Check if user is already a member
    existing_membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    if existing_membership:
        flash('You are already a member of this club!', 'info')
        return redirect(url_for('main.view_club', club_id=club_id))

    # Create a new membership
    membership = Membership(user_id=current_user.id, club_id=club.id)
    db.session.add(membership)
    db.session.commit()

    flash(f'You have successfully joined {club.name}!', 'success')
    return redirect(url_for('main.view_club', club_id=club_id))

@main.route('/club/<int:club_id>/leave', methods=['POST'])
@login_required
def leave_club(club_id):
    club = Club.query.get_or_404(club_id)

    # Find the membership record
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id).first()

    # If no membership found, flash a message and redirect
    if not membership:
        flash('You are not a member of this club!', 'warning')
        return redirect(url_for('main.view_club', club_id=club_id))

    # If the user is an admin, prevent them from leaving without transferring ownership
    if membership.role == 'admin':
        flash('Admins cannot leave the club. You need to assign another admin first.', 'danger')
        return redirect(url_for('main.view_club', club_id=club_id))

    # Remove the membership
    db.session.delete(membership)
    db.session.commit()

    flash(f'You have left {club.name}.', 'info')
    return redirect(url_for('main.view_club', club_id=club_id))

# Route to view members of the club
@main.route('/club/<int:club_id>/members')
@login_required
def view_members(club_id):
    club = Club.query.get_or_404(club_id)

    page = request.args.get('page', 1, type=int)
    filterr = request.args.get('filter', 'all')

    if filterr == 'moderators':
        # Filter only admin and moderator members
        members = Membership.query.filter_by(club_id=club_id).filter(Membership.role.in_(['admin', 'moderator'])).paginate(page=page, per_page=10)
    else:
        # Show all members
        members = Membership.query.filter_by(club_id=club_id).paginate(page=page, per_page=10)

    # Check if the current user is an admin
    current_user_is_admin = False
    current_user_membership = Membership.query.filter_by(club_id=club_id, user_id=current_user.id).first()
    if current_user_membership and current_user_membership.role == 'admin':
        current_user_is_admin = True

    return render_template('view_members.html', club=club, members=members, current_user_is_admin = current_user_is_admin, filterr=filterr)

@main.route('/club/<int:club_id>/create_event', methods=['GET', 'POST'])
@login_required
def create_event(club_id):
    form = EventForm()
    club = Club.query.get_or_404(club_id)

    if form.validate_on_submit():
        new_event = Event(
            name=form.name.data,
            description=form.description.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            club_id=club_id,
            organizer_id=current_user.id
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('main.view_club', club_id=club_id))

    return render_template('create_event.html', form=form, club=club)

@main.route('/club/event/<int:event_id>/join', methods=['POST'])
@login_required
def join_event(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user in event.participants:
        flash('You have already joined this event.', 'warning')
    else:
        event.participants.append(current_user)
        db.session.commit()
        flash('You have joined the event!', 'success')
    return redirect(url_for('main.view_club', club_id=event.club_id))

@main.route('/club/event/<int:event_id>/leave', methods=['POST'])
@login_required
def leave_event(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user in event.participants:
        event.participants.remove(current_user)
        db.session.commit()
        flash('You have left the event.', 'info')
    else:
        flash('You are not part of this event.', 'warning')
    return redirect(url_for('main.view_club', club_id=event.club_id))

# Route to promote a member to moderator or admin
@main.route('/club/<int:club_id>/promote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def promote_member(club_id, user_id):
    membership = Membership.query.filter_by(club_id=club_id, user_id=user_id).first()
    if membership and membership.role != 'admin':
        membership.role = request.form.get('role', 'moderator')  # Default is 'moderator'
        db.session.commit()
        flash(f'Member {membership.user_id} has been promoted to {membership.role}.', 'success')
    return redirect(url_for('main.view_members', club_id=club_id))

# Route to remove a member
@main.route('/club/<int:club_id>/remove/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_member(club_id, user_id):
    membership = Membership.query.filter_by(club_id=club_id, user_id=user_id).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()
        flash(f'Member {membership.user_id} has been removed.', 'success')
    return redirect(url_for('main.view_members', club_id=club_id))
    
# 4 - User Profiles

def fetch_book_info(book_id):
    url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4XX/5XX errors
        data = response.json()

        # Extract book details
        book_info = data.get('volumeInfo', {})
        title = book_info.get('title', 'No Title')
        authors = book_info.get('authors', ['Unknown Author'])
        thumbnail = book_info.get('imageLinks', {}).get('thumbnail', '')
        published_date = book_info.get('publishedDate', 'Unknown')

        return {
            'book_id': book_id,
            'title': title,
            'author': authors[0] if authors else 'Unknown Author',
            'thumbnail': thumbnail,
            'published_date': published_date
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching book data: {e}")
        return None

@main.route('/user/<username>')
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    clubs = Club.query.join(Membership).filter(Membership.user_id == user.id).all()

    favorite_books = []
    for book in user.favorite_books:
        book_data = fetch_book_info(book)
        favorite_books.append(book_data)        
    
    return render_template('profile.html', user=user, clubs=clubs, favorite_books=favorite_books)

@main.route('/create_bookshelf', methods=['GET', 'POST'])
@login_required
def create_bookshelf():
    form = BookshelfForm()
    if form.validate_on_submit():
        # Check if the description is provided
        description = form.description.data or "This is a default description for the bookshelf."
        bookshelf = Bookshelf(name=form.name.data, description=description, user_id=current_user.id)
        db.session.add(bookshelf)
        db.session.commit()
        flash('Your bookshelf has been created!', 'success')
        return redirect(url_for('main.view_profile', username=current_user.username))
    return render_template('create_bookshelf.html', form=form)

@main.route('/user/<username>/bookshelves/<bookshelf_name>')
def view_bookshelves(username, bookshelf_name):
    bookshelves = Bookshelf.query.join(User).filter(User.username == username).all()
    selected_shelf = Bookshelf.query.join(User).filter(User.username == username, Bookshelf.name == bookshelf_name).first()

    books_list = []
    for book in selected_shelf.books:
        book_info = fetch_book_info(book)
        if book_info:
            books_list.append(book_info)

    # Pagination logic
    page = request.args.get('page', 1, type=int)
    books_per_page = 6 # Adjust this as needed
    start = (page - 1) * books_per_page
    end = start + books_per_page
    books = books_list[start:end]

    # Calculate total pages
    total_pages = (len(books_list) + books_per_page - 1) // books_per_page

    return render_template('view_bookshelf.html', bookshelves=bookshelves, books=books, selected_shelf=selected_shelf, username=username, total_pages=total_pages, current_page=page)

@main.route('/user/<username>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user != current_user:
        abort(403)

    form = ProfileForm(obj=user)
    if form.validate_on_submit():
        user.bio = form.bio.data
        user.profile_picture = form.profile_picture.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('main.view_profile', username=user.username))

    return render_template('edit_profile.html', form=form)

@main.route('/')
@main.route('/home')
def home():
    books = Book.query.all()
    clubs = Club.query.all()

    # Sort books by average rating and review count, then take the top 3
    featured_books = Book.query.all()
    featured_clubs = clubs

    return render_template('home.html', featured_books=featured_books, featured_clubs=featured_clubs)

@main.route('/land')
def land():
    return render_template('land.html')

def fetch_book_details(title, author):
    # Search for the book on Google Books API
    api_url = f'https://www.googleapis.com/books/v1/volumes?q=intitle:{title}+inauthor:{author}'
    response = requests.get(api_url)

    if response.status_code == 200:
        books = response.json().get('items', [])
        if not books:
            return None

        # Initialize variables to store the best book
        best_book = None

        # Prioritize books that have both description and thumbnail
        for book in books:
            volume_info = book.get('volumeInfo', {})
            has_description = 'description' in volume_info
            has_thumbnail = 'imageLinks' in volume_info and 'thumbnail' in volume_info['imageLinks']

            # Prioritize books with both description and thumbnail
            if has_description and has_thumbnail:
                best_book = volume_info
                book_id = book.get('id')
                break  # Found the best match, no need to continue searching

        # If no book with both description and thumbnail, look for a book with at least a description
        if not best_book:
            for book in books:
                volume_info = book.get('volumeInfo', {})
                if 'description' in volume_info:
                    best_book = volume_info
                    book_id = book.get('id')
                    break

        # If still no match, take the first book with or without description
        if not best_book and books:
            best_book = books[0].get('volumeInfo', {})
            book_id = book.get('id')

        # Return book info with a fallback thumbnail
        return {
            'id': book_id,
            'title': best_book.get('title', 'Unknown Title'),
            'author': ', '.join(best_book.get('authors', ['Unknown Author'])),
            'genre': ', '.join(best_book.get('categories', ['Unknown Genre'])),
            'description': best_book.get('description', 'No description available.'),
            'thumbnail': best_book.get('imageLinks', {}).get('thumbnail')
        }

    return None  # If API call failed or no books found

def scrape_books():
    with current_app.app_context():
        print("start of scrapping books")
        current_month = datetime.now().strftime('%m')
        current_year = datetime.now().year

        url = f'https://www.goodreads.com/book/popular_by_date/{current_year}/{current_month}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', class_='BookListItem')
            scraped_books = []
            for article in articles:
                title = article.find('h3', class_='Text Text__title3 Text__umber').get_text(strip=True).split('(')[0].strip()
                author = article.find('span', class_='ContributorLink__name').get_text(strip=True)
                scraped_books.append((title, author))

        else:
            print(f"Failed to retrieve the webpage. Status code: {response.status_code}")

        for book in scraped_books:
            details = fetch_book_details(book[0], book[1])
            if details:
                existing_book = Book.query.filter_by(year=current_year, month=current_month, title=book[0]).first()
                if not existing_book:
                    new_book = Book(
                        year=current_year,
                        month=current_month,
                        book_id=details['id'],
                        title=details['title'],
                        author=details['author'],
                        genre=details['genre'],
                        description=details['description'],
                        thumbnail=details['thumbnail']
                        )
                    db.session.add(new_book)
                db.session.commit()

# Function to fetch books using Google Books API
def fetch_books(query, max_results=105, items_per_page=40, book_id=0):
    api_url = "https://www.googleapis.com/books/v1/volumes"
    all_books = []
    start_index = 0

    if book_id:
        url = f"{api_url}/{book_id}"
        response = requests.get(url)
        data = response.json()
        return data

    # Loop through paginated results from the Google Books API
    while start_index < max_results:
        # Parameters for the API request
        params = {
            'q': query,
            'startIndex': start_index,
            'maxResults': items_per_page  # Google Books API allows up to 40 results per request
        }
        response = requests.get(api_url, params=params)
        data = response.json()

        # If 'items' key exists in the response, append the results to all_books
        if 'items' in data:
            all_books.extend(data['items'])
        else:
            break  # No more items to fetch, break the loop

        # Move to the next page of results
        start_index += items_per_page

    return all_books

# Function to clean up the description
def clean_description(description):
    return bleach.clean(description, tags=[], strip=True)  # Strip all HTML tags

@club_bp.route('/view_book/<book_id>', methods=['GET', 'POST'])
def view_book(book_id):
    book = fetch_books('none', book_id=book_id)
    # Get all bookshelves for the current user
    bookshelves = Bookshelf.query.filter_by(user_id=current_user.id).all()

    # Check for the response
    if book.get('error'):
        abort(404)
    
    # Clean the description
    description = book['volumeInfo'].get('description', 'No description found')
    clean_desc = clean_description(description)

    # Handle the Review form
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            content=form.content.data,
            rating=form.rating.data,
            user_id=current_user.id,
            book_id=book_id
        )
        flash('Your review has been added!', 'success')
        return redirect(url_for('club_bp.view_book', book_id=book.get('id')))

    # Search for related books
    categories = book['volumeInfo'].get('categories', ['Unknown Genre'])

    # handle all words correctly and get the unique set of words from the categories list.
    if categories:
        unique_genres = set()
        for category in categories:
            phrases = category.split(" / ")
            for phrase in phrases:
                words = phrase.split()
                unique_genres.update(words)

        query = '+'.join(unique_genres)
        related_books = fetch_books(query, max_results=20, items_per_page=10)
    else:
        parsed_title = book['volumeInfo'].get('title').split()
        query = '+'.join(parsed_title)
        related_books = fetch_books(query, max_results=20, items_per_page=10)

    return render_template('view_book.html', book=book, clean_desc=clean_desc, reviews=[], form=form, related_books=related_books, bookshelves=bookshelves)

# Check if a JSON file exists in the current directory
def json_file_exists(directory):
    # List all files in the given directory
    files = os.listdir(directory)

    # Find any JSON files
    json_files = [file for file in files if file.endswith('.json')]

    if json_files:
        # Return the first JSON file found (assuming there's only one relevant file)
        return json_files[0]
    else:
        return None

# Function to load a JSON file
def load_json_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data  # Return the JSON data as a Python object
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

# Main route for displaying books
@main.route('/books', methods=['GET', 'POST'])
@login_required
def books():
    # Get all bookshelves for the current user
    bookshelves = Bookshelf.query.filter_by(user_id=current_user.id).all()

    ITEMS_PER_PAGE = 9  # Number of books to display per page

    # Get current page from query parameters or default to 1
    page = int(request.args.get('page', 1))
    query = request.form.get('query') if request.method == 'POST' else request.args.get('query', '')

    # Construct the JSON filename based on the search query
    json_file = f"{query}-search.json"
    json_file_path = json_file_exists(os.getcwd())  # Check if a JSON file already exists

    # Check if the existing JSON file matches the current query
    if json_file_path:
        if json_file == json_file_path:
            # Load the existing filtered books from the JSON file
            filtered_books = load_json_file(json_file_path)
        else:
            # Remove the old JSON file if the query has changed
            os.remove(json_file_path)
            filtered_books = []
    else:
        # No JSON file found, so we need to fetch the books
        filtered_books = []

    # If query exists and filtered_books is empty, fetch books from the API
    if query and not filtered_books:
        # Split the search query into terms and convert them to lowercase
        search_terms = [word.lower() for word in query.split(' ')]
        all_books = fetch_books(query)  # Fetch books from Google Books API

        filtered_books = []  # Initialize filtered books list
        id = 0
        for book in all_books:
            # Extract relevant fields from each book
            title = book['volumeInfo'].get('title', '').lower()
            subtitle = book['volumeInfo'].get('subtitle', '').lower()
            language = book['volumeInfo'].get('language', '')

            # Only include English books that match the search terms
            if language == "en":
                combined_text = f"{title} {subtitle}"
                if all(term in combined_text for term in search_terms):
                    # Append filtered book details in a more compact format
                    filtered_books.append({
                        'id': book['id'], 
                        'title': book['volumeInfo'].get('title', ''),
                        'subtitle': book['volumeInfo'].get('subtitle', ''),
                        'authors': book['volumeInfo'].get('authors', ['Unknown author']),
                        'publisher': book['volumeInfo'].get('publisher', 'Unknown Publisher'),
                        'publishedDate': book['volumeInfo'].get('publishedDate', ''),
                        'thumbnail': book['volumeInfo'].get('imageLinks', {}).get('thumbnail', 'https://www.peeters-leuven.be/covers/no_cover.gif'),
                        'description': book['volumeInfo'].get('description', 'No description found, we will add it later :).')
                    })

        # Save filtered books to a JSON file for future use
        with open(json_file, 'w') as f:
            json.dump(filtered_books, f)

    # Pagination logic: Calculate total pages and the books to display on the current page
    total_items = len(filtered_books)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    paginated_books = filtered_books[start:end]

    # Fetch the popular books of the current month (this is specific to your application)
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    books = Book.query.filter_by(year=current_year, month=current_month).all()
    if not books:
        scrape_books()
        books = Book.query.filter_by(year=current_year, month=current_month).all()

    # Render the template with the relevant data
    return render_template(
        'books.html',
        books=books,
        bookshelves=bookshelves,
        filtered_books=paginated_books,
        query=query,
        total_items=total_items,
        total_pages=total_pages,
        page=page
    )

@main.route('/a', methods=['GET', 'POST'])
def a():
    return render_template('a.html')

@main.route('/add-to-shelf', methods=['POST'])
def add_to_shelf():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        # Check if data is valid
        if not data or 'book_id' not in data or 'shelf' not in data:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400

        book_id = data['book_id']
        selected_shelf = data['shelf']

        # Fetch the bookshelf for the current user with the selected shelf name
        bookshelf = Bookshelf.query.filter_by(user_id=current_user.id, name=selected_shelf).first()

        if bookshelf:
            # Ensure books is a list and not None
            if bookshelf.books is None:
                bookshelf.books = []

            # Remove the book from any other shelf
            other_bookshelves = Bookshelf.query.filter_by(user_id=current_user.id).all()
            for other_shelf in other_bookshelves:
                if (other_shelf != bookshelf) and (book_id in other_shelf.books):
                    other_shelf.books.remove(book_id)

            # Add the book_id to the selected bookshelf if not already present
            if book_id not in bookshelf.books:
                bookshelf.books.append(book_id)
                db.session.commit()
                return jsonify({'success': True}), 200
            else:
                print("Book already in the selected shelf")
                return jsonify({'success': False, 'error': 'Book already in the selected shelf'}), 400
        else:
            return jsonify({'success': False, 'error': 'Bookshelf not found'}), 404

    except Exception as e:
        # Handle any unexpected errors
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/remove-from-shelf', methods=['POST'])
def remove_from_shelf():
    data = request.get_json()
    book_id = data.get('book_id')
    shelf_name = data.get('shelf')
    print(book_id)
    print(shelf_name)

    # Find the user's bookshelf with the given name
    bookshelf = Bookshelf.query.filter_by(user_id=current_user.id, name=shelf_name).first()
    
    if bookshelf:
        # Remove the book ID from the bookshelf
        if book_id in bookshelf.books:
            bookshelf.books.remove(book_id)
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Book not found in the specified shelf"}), 404
    else:
        return jsonify({"success": False, "error": "Shelf not found"}), 404
