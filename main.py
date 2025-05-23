from flask import Flask, render_template, request, redirect,session,url_for,send_from_directory
from graphene import ObjectType, Schema, Int
from graphene_sqlalchemy import SQLAlchemyObjectType
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import graphene
from flask_sqlalchemy import SQLAlchemy
from flask_graphql import GraphQLView
from flask_login import LoginManager,UserMixin,logout_user,login_user
from flask_login import login_required,current_user
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask import jsonify
from flask_jwt_extended import JWTManager,create_access_token,jwt_required, get_jwt_identity
from flask import flash
from graphql import GraphQLError
from sqlalchemy.orm import sessionmaker
import sqlalchemy as db_module
from flask_paginate import Pagination, get_page_args
from werkzeug.utils import secure_filename
import os
from flask_mail import Mail, Message
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')
from functools import wraps

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('admin_panel'))
        return func(*args, **kwargs)
    return decorated_view

SWAGGER_URL = '/swagger'  
API_URL = '/static/swagger.json'  

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, 
    API_URL,
    config={ 
        'app_name': "Book Management System"
    },
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

app.config['JWT_SECRET_KEY'] = 'your-secret-key'  
app.config['UPLOAD_FOLDER'] = 'static'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SECRET_KEY'] = '9494'
db = SQLAlchemy(app)
jwt = JWTManager(app)
login_manager = LoginManager(app)
login_manager.init_app(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'kevinjagani9428@gmail.com'
app.config['MAIL_PASSWORD'] = 'vlvf izes rlln lmfm'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'
mail = Mail(app)

class User(db.Model, UserMixin):
    __tablename__ = "user"  
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 
    reviews = relationship("Review", back_populates="user")

    books = relationship("Book", back_populates="user")


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, index=True)
    author = db.Column(db.String, index=True)
    published_date = db.Column(db.Date)
    isbn = db.Column(db.String, index=True)
    num_pages = db.Column(db.Integer)
    cover_image_url = db.Column(db.String, nullable=True)
    genre = db.Column(db.String) 
    publisher = db.Column(db.String)  
    language = db.Column(db.String)  
    description = db.Column(db.String)  
    ratings = db.Column(db.Float)  

    user_id = db.Column(db.Integer, ForeignKey('user.id')) 
    reviews = relationship("Review", back_populates="book")
    

    user = relationship("User", back_populates="books")
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'published_date': self.published_date.strftime('%Y-%m-%d'), 
            'isbn': self.isbn,
            'num_pages': self.num_pages,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre, 
            'publisher': self.publisher,
            'language': self.language,
            'description': self.description,
            'ratings': self.ratings
        }


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rating = db.Column(db.Integer)
    comment = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship("User", back_populates="reviews")

    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    book = relationship("Book", back_populates="reviews")

class UserType(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the user", required=True)

    def resolve_id(self, info):
        return str(self.id)

class BookType(SQLAlchemyObjectType):
    class Meta:
        model = Book
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the book", required=True)
    reviews = graphene.List(lambda: ReviewType)

    def resolve_id(self, info):
        return str(self.id)

    def resolve_reviews(self, info):
        return [review for review in self.reviews]

class ReviewType(SQLAlchemyObjectType):
    class Meta:
        model = Review
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the review", required=True)
    user = graphene.String() 
    book = graphene.String() 
    def resolve_user(self, info):
        return f"/users/{self.user_id}"

    def resolve_book(self, info):
        return f"/books/{self.book_id}"

@login_manager.user_loader
def loader_user(user_id):
    return db.session.query(User).get(user_id)
    
with app.app_context():
    db.create_all()


from flask import redirect, url_for, session, request
@app.route('/admin/panel')

def admin_panel():
    books_with_users = db.session.query(Book, User).join(User).all()
    total_books = db.session.query(Book).count()
    total_users = db.session.query(User).count()

    return render_template('admin_panel.html', books_with_users=books_with_users, total_books=total_books, total_users=total_users)


    
from flask import redirect, flash

@app.route('/login', methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash('Both email and password are required!!', 'login_error')
            return redirect(url_for('login_page'))
        user = db.session.query(User).filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            access_token=create_access_token(identity=user.id)
            login_user(user)

            return redirect(url_for("index", message="Login successful, welcome {}!".format(user.name)))
        else:
            flash('Invalid email or password', 'login_error')
            return redirect(url_for('login_page'))
            
    elif request.method == "GET":
        return render_template('login.html')

@app.route('/register', methods=["POST"])
def register_page():
    email = request.form.get("email")
    password = request.form.get("password")
    name = request.form.get('name')
    
    if not email  or not password or not name :
        flash('Please fill all required fields', 'signup_error')
        return redirect(url_for('login_page'))

    if not name.isalpha():
        flash('Name must contain only letters', 'signup_error')
        return redirect(url_for('login_page'))

    if db.session.query(User).filter_by(email=email).first():
        flash('Email already exists', 'signup_error')
        return redirect(url_for('login_page'))

    if not password:
        flash('Password is required', 'signup_error')
        return redirect(url_for('login_page'))

    user = User(email=email, password=password, name=name)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    login_user(user) 
    send_welcome_email(email)
    flash('Registration successful!', 'success')

    return redirect(url_for("index"))

    flash('Please fill all required fields', 'signup_error')
    return redirect(url_for('login_page'))

from sqlalchemy import or_
from flask import jsonify

@app.route('/search')
@login_required 
def search():
    search_query = request.args.get('q')
    
    user_id = current_user.id  

    search_results = Book.query.filter(
        (Book.user_id == user_id) &
        (or_(
            Book.title.ilike(f'%{search_query}%'),
            Book.author.ilike(f'%{search_query}%'),
            Book.genre.ilike(f'%{search_query}%'),  
            Book.ratings.ilike(f'%{search_query}%'),  
            Book.published_date.ilike(f'%{search_query}%'),  
            Book.language.ilike(f'%{search_query}%')  
        ))
    ).all()
    if not search_results:
        return jsonify({'message': 'No results found for the given query.'}), 404   
    search_results_json = [book.serialize() for book in search_results]
    
    return jsonify(search_results_json)

@app.route('/logout', methods=["GET", "POST"])
@login_required
def logout():
    logout_user() 
    return redirect(url_for('login_page'))


@app.route('/protected', methods=['GET', 'POST'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return {'messege':"hello user {current_user_id}"}, 200


@app.route('/')
def index():
    if 'user_id' in session:  
        user_id = session['user_id']
        message = request.args.get('message')
        
        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
        books = db.session.query(Book).filter(Book.user_id == user_id).offset(offset).limit(per_page).all()

        pagination = Pagination(page=page, total=len(books), record_name='books', per_page=per_page, css_framework='bootstrap4')
        
        return render_template('index.html', books=books, book=None, message=message, pagination=pagination)
    else:
        return redirect(url_for('login_page')) 
        
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    title = request.form.get('title')
    author = request.form.get('author')
    published_date_str = request.form.get('published_date')
    isbn = request.form.get('isbn')
    num_pages = request.form.get('num_pages')
    genre = request.form.get('genre')
    publisher = request.form.get('publisher')
    language = request.form.get('language')
    description = request.form.get('description')
    ratings = request.form.get('ratings')

    if not all([title, author, published_date_str, isbn, num_pages, genre, publisher, language, description, ratings]):
        flash('Please fill in all the required fields.', 'error')
        return redirect(url_for('index'))

    try:
        published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid published date format. Please use YYYY-MM-DD.', 'error')
        return redirect(url_for('index'))

    if 'cover_image' in request.files:
        cover_image = request.files['cover_image']
        if cover_image.filename != '':
            filename = secure_filename(cover_image.filename)
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                flash('Invalid file format for cover image. Only JPG, JPEG, PNG, and GIF are allowed.', 'error')
                return redirect(url_for('index'))
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image_url = url_for('uploaded_file', filename=filename)
        else:
            cover_image_url = None
    else:
        cover_image_url = None

    book = Book(
        title=title, author=author, published_date=published_date,
        isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url,
        genre=genre, publisher=publisher, language=language, description=description,
        ratings=ratings, user_id=session['user_id']
    )
    db.session.add(book)
    db.session.commit()
    send_book_added_notification(current_user.email, title)
    flash('Congratulations! Your book has been successfully added and an email notification has been sent.', 'success')
    return redirect(url_for('index'))



@app.route('/update_book', methods=['PUT'])
@login_required
def update_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.form 
    book_id = data.get('book_id')   

    if book_id is None:
        return jsonify({'error': 'Book ID not provided'}), 400

    book = db.session.query(Book).filter(Book.id == book_id).first()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to update this book'}), 403

    title = data.get('title')
    author = data.get('author')
    published_date_str = data.get('published_date')
    isbn = data.get('isbn')
    num_pages = data.get('num_pages')
    cover_image_url = None

    if 'cover_image' in request.files:
        cover_image = request.files['cover_image']
        if cover_image.filename != '':
            filename = secure_filename(cover_image.filename)
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                return jsonify({'error': 'Invalid file format'}), 400
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image_url = url_for('uploaded_file', filename=filename)

    genre = data.get('genre')
    publisher = data.get('publisher')
    language = data.get('language')
    description = data.get('description')
    ratings = data.get('ratings')

    if title:
        book.title = title
    if author:
        book.author = author
    if published_date_str:
        book.published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    if isbn:
        book.isbn = isbn
    if num_pages:
        book.num_pages = num_pages
    if cover_image_url:
        book.cover_image_url = cover_image_url
    if genre:
        book.genre = genre
    if publisher:
        book.publisher = publisher
    if language:
        book.language = language
    if description:
        book.description = description
    if ratings:
        book.ratings = ratings

    db.session.commit()
    send_book_updated_notification(current_user.email, title)
    return jsonify({
        'success': True,
        'message': 'Book updated successfully',
        'data': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'published_date': book.published_date.strftime('%Y-%m-%d') if book.published_date else None,
            'isbn': book.isbn,
            'num_pages': book.num_pages,
            'cover_image_url': book.cover_image_url,
            'genre': book.genre,
            'publisher': book.publisher,
            'language': book.language,
            'description': book.description,
            'ratings': book.ratings
        }
    }), 200


@app.route('/delete_book/<int:book_id>', methods=['delete'])
@login_required
def delete_book(book_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    book = db.session.query(Book).filter(Book.id == book_id).first()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to delete this book'}), 403
    title = book.title
    db.session.delete(book)
    db.session.commit()
    send_book_deleted_notification(current_user.email, title)
    return jsonify({'success': True, 'message': 'Book delete successfully'}), 201
    return redirect(url_for('index'))

def send_welcome_email(user_email):
    msg = Message('Welcome to Book Management System', recipients=[user_email])
    msg.body = 'Dear user, Welcome to Book Management System! Thank you for registering.'
    mail.send(msg)

def send_book_added_notification(user_email, book_title):
    msg = Message('Book Added', recipients=[user_email])
    msg.body = f'Dear user, You have added a new book: {book_title}.'
    mail.send(msg)

def send_book_updated_notification(user_email, book_title):
    msg = Message('Book Updated', recipients=[user_email])
    msg.body = f'Dear user, You have updated the book: {book_title}.'
    mail.send(msg)

def send_book_deleted_notification(user_email, book_title):
    msg = Message('Book Deleted', recipients=[user_email])
    msg.body = f'Dear user, You have deleted the book: {book_title}.'
    mail.send(msg)


@app.route('/all_books')

def all_books():
    all_books = db.session.query(Book).all()

    books_list = []
    for book in all_books:
        user_data = None
        if book.user:
            user_data = {
                'id': book.user.id,
                'name': book.user.name,
            }
        rating_count = len(book.reviews)
        if rating_count > 0:
            average_rating = sum(review.rating for review in book.reviews) / rating_count
        else:
            average_rating = 0
       
        books_list.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'published_date': str(book.published_date),   
            'genre': book.genre,
            'cover_image_url': book.cover_image_url, 
            'user': user_data,
            'rating_count': rating_count,
            'average_rating': average_rating
        })

    return jsonify({'books': books_list})

@app.route('/books', methods=['GET'])
def render_review():
     return render_template('book.html')

@app.route('/books', methods=['GET'])
def render_review():
    book = Book.query.all()

    return render_template('book.html', book=book)

@app.route('/get_reviews')
def get_reviews():
    reviews = Review.query.all()
    review_data = []
    for review in reviews:
        review_data.append({
            'id': review.id,
            'user_id': review.user_id,
            'user_name': review.user.name,
            'book_id': review.book_id,
            'book_title': review.book.title,
            'rating': review.rating,
            'comment': review.comment,
            'timestamp': review.timestamp.strftime('%Y-%m-%d %H:%M:%S') 
        })
    return jsonify({'reviews': review_data})

@app.route('/create_review', methods=['GET'])
@login_required
def render_review_form():
    book_id = request.args.get('book_id')
    if not book_id:
        return jsonify({'error': 'Book ID not provided'}), 400
    user_id = request.args.get('user_id')
  
    return render_template('review.html', book_id=book_id, user_id=user_id)

@app.route('/create_review', methods=['POST'])
@login_required
def handle_review_submission():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = request.get_json()
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    rating = int(data.get('rating')) if data.get('rating') is not None else None
    comment = data.get('comment')
    timestamp_str = data.get('timestamp')
    book = Book.query.get(book_id)
    user = User.query.get(user_id)
    if not book:
        return jsonify({'error': f"Book with ID {book_id} not found"}), 404
    if not user:
        return jsonify({'error': f"User with ID {user_id} not found"}), 404
    user = db.session.query(User).get(user_id)
    book = db.session.query(Book).get(book_id)

    if not user:
         return jsonify({'error': f"User with ID {user_id} not found"}), 404
    if not book:
         return jsonify({'error': f"Book with ID {book_id} not found"}), 404

    timestamp = datetime.fromisoformat(timestamp_str)
    review = Review(
        user=user,
        user_id=user_id,
        book_id=book_id,
        book=book,
        rating=rating,
        comment=comment,
        timestamp=timestamp if timestamp else datetime.utcnow()
    )

    db.session.add(review)
    db.session.commit()

    return jsonify({'success': 'Review created successfully'}), 200



@app.route('/update_review', methods=['PUT'])
@login_required
def update_review():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()   
    review_id = request.form.get('review_id')   

    if review_id is None:
        return jsonify({'error': 'Review ID not provided'}), 400

    review = db.session.query(Review).filter(Review.id == review_id).first()

    if review is None:
        return jsonify({'error': 'Review not found'}), 404

    if review.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to update this review'}), 403

    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if rating is not None:
        review.rating = rating
    if comment:
        review.comment = comment

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Review updated successfully',
        'data': {
            'id': review.id,
            'user_id': review.user_id,
            'book_id': review.book_id,
            'rating': review.rating,
            'comment': review.comment,
            'timestamp': review.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    }), 200

@app.route('/delete_review', methods=['post'])
@login_required
def delete_review():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()
    review_id = data.get('review_id')

    if review_id is None:
        return jsonify({'error': 'Invalid review ID provided'}), 400

    review = db.session.query(Review).get(review_id)

    if not review:
        return jsonify({'error': f"Review with ID {review_id} not found"}), 404

    db.session.delete(review)
    db.session.commit()

    return jsonify({'success': 'Review deleted successfully'}), 200


class Query(ObjectType):
     books = graphene.List(BookType)
     book = graphene.Field(BookType, id=graphene.Int())
     books_by_genre = graphene.List(BookType, genre=graphene.String())
   

     def resolve_books(self, info):
         return SessionLocal().query(Book).all()

     def resolve_book(self, info, id):
         return SessionLocal().query(Book).filter(Book.id == id).first()

     def resolve_books_by_genre(self, info, genre):
         return SessionLocal().query(Book).filter(Book.genre == genre).all()

    
class Query(ObjectType):
    reviews = graphene.List(ReviewType)
    users = graphene.List(UserType)
    books = graphene.List(BookType)
    book = graphene.Field(BookType, id=graphene.ID())

    def resolve_reviews(self, info):
        return db.session.query(Review).all()

    def resolve_users(self, info):
        return db.session.query(User).all()

    def resolve_books(self, info):
        return db.session.query(Book).all()

    def resolve_book(self, info, id):
        return db.session.query(Book).get(id)

class Query(ObjectType):
     reviews = graphene.List(ReviewType)
     users = graphene.List(UserType)
     def resolve_reviews(self, info):
         return db.session.query(Review).all()
     def resolve_users(self, info):
         return db.session.query(User).all()
     def resolve_books(self,info):
         return db.session.query(Book).all()
    
class CreateReview(graphene.Mutation):
        class Arguments:
            user_id = graphene.Int(required=True)
            book_id = graphene.Int(required=True)
            rating = graphene.Int(required=True)
            comment = graphene.String()
            timestamp = graphene.DateTime()

        review = graphene.Field(ReviewType)

        def mutate(self, info, user_id, book_id, rating, comment=None, timestamp=None):
            if not 1 <= rating <= 5:
                raise GraphQLError("Rating must be between 1 and 5")
            user = db.session.query(User).get(user_id)
            book = db.session.query(Book).get(book_id)

            if not user:
                raise GraphQLError(f"User with ID {user_id} not found")
            if not book:
                raise GraphQLError(f"Book with ID {book_id} not found")

            review = Review(
                user=user,
                book=book,
                rating=rating,
                comment=comment,
                timestamp=timestamp if timestamp else datetime.utcnow()
            )

            db.session.add(review)
            db.session.commit()

            return CreateReview(review=review)

class DeleteReview(graphene.Mutation):
        class Arguments:
            reviewId = graphene.Int(required=True)

        success = graphene.Boolean()

        def mutate(self, info, reviewId):
            review = db.session.query(Review).get(reviewId)

            if not review:
                raise GraphQLError(f"Review with ID {reviewId} not found")

            db.session.delete(review)
            db.session.commit()

            return DeleteReview(success=True)


class CreateBook(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        author = graphene.String()
        published_date = graphene.Date()
        isbn = graphene.String()
        num_pages = graphene.Int()
        cover_image_url = graphene.String()
        genre = graphene.String()
        publisher = graphene.String()
        language = graphene.String()
        description = graphene.String()
        ratings = graphene.Float()
    book = graphene.Field(BookType)

    def mutate(self, info,  title, author, published_date, isbn, num_pages, cover_image_url, genre, publisher, language, description, ratings):
        db = ()
        book = Book(title=title, author=author, published_date=published_date,
                isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url,genre=genre,publisher=publisher,language=language,description=description,ratings=ratings)
        db.add(book)
        db.commit()
        db.refresh(book)
        return CreateBook(book=book)


class UpdateBook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String(required=True)
        author = graphene.String()
        published_date = graphene.Date()
        isbn = graphene.String()
        num_pages = graphene.Int()
        cover_image_url = graphene.String()
        genre = graphene.String()
        publisher = graphene.String()
        language = graphene.String()
        description = graphene.String()
        ratings = graphene.Float()

    book = graphene.Field(BookType)

    def mutate(self, info, id, title, author, published_date, isbn, num_pages, cover_image_url, genre, publisher, language, description, ratings):
        db = ()
        book=db.query(Book).filter(Book.id == id).first()
        if not book:
            raise Exception(f"Book with id {id} not found")

        book.title = title
        book.author = author
        book.published_date = published_date
        book.isbn = isbn
        book.num_pages = num_pages
        book.cover_image_url = cover_image_url
        book.genre = genre
        book.publisher = publisher
        book.language = language
        book.description = description
        book.ratings = ratings

        db.commit()
        db.refresh(book)
        return UpdateBook(book=book)

class DeleteBook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    book = graphene.Field(BookType)
    def mutate(self,info,id):
        db = ()
        book=db.query(Book).filter(Book.id == id).first()
        if not book:
             raise Exception(f"Book with id {id} not found")
        db.delete(book)
        db.commit()
        return DeleteBook(book=book)

class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()
    update_book = UpdateBook.Field()
    delete_book = DeleteBook.Field()
    create_review = CreateReview.Field()
    delete_review = DeleteReview.Field()

schema = Schema(query=Query,mutation=Mutation)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)
