from flask import Flask, render_template, request, redirect,session,url_for
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

app = Flask(__name__)
# csrf = CSRFProtect(app)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to a random secret key

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SECRET_KEY'] = '9494'
db = SQLAlchemy(app)
jwt = JWTManager(app)
login_manager = LoginManager(app)
login_manager.init_app(app)

class User(db.Model, UserMixin):
    __tablename__ = "user"  # <-- Update the table name to 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    reviews = relationship("Review", back_populates="user")
      # Define relationship with books
    books = relationship("Book", back_populates="user")

# Define SQLAlchemy models
class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, index=True)
    author = db.Column(db.String, index=True)
    published_date = db.Column(db.Date)
    isbn = db.Column(db.String, index=True)
    num_pages = db.Column(db.Integer)
    cover_image_url = db.Column(String, nullable=True)
    genre = db.Column(db.String) 
    publisher = db.Column(db.String)  
    language = db.Column(db.String)  
    description = db.Column(db.String)  
    ratings = db.Column(db.Float)  

    user_id = db.Column(db.Integer, ForeignKey('user.id'))  # Define user_id column and establish a ForeignKey relationship
    reviews = relationship("Review", back_populates="book")
    
    # Define relationship with User
    user = relationship("User", back_populates="books")
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'published_date': self.published_date.strftime('%Y-%m-%d'),  # Format date as string
            'isbn': self.isbn,
            'num_pages': self.num_pages,
            'cover_image_url': self.cover_image_url,
            'genre': self.genre,  # Serialize new fields
            'publisher': self.publisher,
            'language': self.language,
            'description': self.description,
            'ratings': self.ratings
        }

# Add this to your existing SQLAlchemy models
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

# Define GraphQL types
class BookType(SQLAlchemyObjectType):
    class Meta:
        model = Book
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the book", required=True)

    def resolve_id(self, info):
        return str(self.id)

    
class ReviewType(SQLAlchemyObjectType):
    class Meta:
        model = Review
        interfaces = (graphene.relay.Node,)

    # Define fields for user, book, rating, comment, and timestamp
    user = graphene.Field(UserType)
    book = graphene.Field(BookType)
    rating = graphene.Int()
    comment = graphene.String()
    timestamp = graphene.DateTime()

    # Resolve the user field to retrieve the corresponding user object
    def resolve_user(self, info):
        return self.user

    # Resolve the book field to retrieve the corresponding book object
    def resolve_book(self, info):
        return self.book

    # Resolve the timestamp field to format the timestamp as a DateTime object
    def resolve_timestamp(self, info):
        return self.timestamp

# Create database tables
# Base.metadata.create_all(bind=engine)

@login_manager.user_loader
def loader_user(user_id):
    return db.session.query(User).get(user_id)

with app.app_context():
    db.create_all()


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
    
    # Check if required fields are not None
    if not email  or not password or not name :
        flash('Please fill all required fields', 'signup_error')
        return redirect(url_for('login_page'))

    # Check if name contains only letters
    if not name.isalpha():
        flash('Name must contain only letters', 'signup_error')
        return redirect(url_for('login_page'))

    # Check if email already exists
    if db.session.query(User).filter_by(email=email).first():
        flash('Email already exists', 'signup_error')
        return redirect(url_for('login_page'))

    if not password:
        flash('Password is required', 'signup_error')
        return redirect(url_for('login_page'))

    # Create the user
    user = User(email=email, password=password, name=name)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    login_user(user)  # Automatically login user after registration
    flash('Registration successful!', 'success')
    return redirect(url_for("index"))

    # Return to login page if registration fails
    flash('Please fill all required fields', 'signup_error')
    return redirect(url_for('login_page'))

from sqlalchemy import or_
from flask import jsonify

@app.route('/search')
@login_required  # Restrict access to logged-in users only
def search():
    search_query = request.args.get('q')
    
    user_id = current_user.id  # Get the ID of the logged-in user
    # Filter the search results based on the logged-in user's ID
    search_results = db_module.session.query(Book).filter(
        (Book.user_id == user_id) & (or_(Book.title.ilike(f'%{search_query}%'), Book.author.ilike(f'%{search_query}%')))
    ).all()
    if not search_results:
        return jsonify({'message': 'No results found for the given query.'}), 404   
    # Serialize search results to JSON
    search_results_json = [book.serialize() for book in search_results]
    
    # Return JSON response
    return jsonify(search_results_json)


@app.route('/logout')
def logout():
    logout_user()  # Remove user id from session
    return redirect(url_for('login_page')) 

@app.route('/protected', methods=['GET', 'POST'])
@jwt_required()
def protected():
    # Access protected resources
    current_user_id = get_jwt_identity()
    return {'messege':"hello user {current_user_id}"}, 200


@app.route('/')
def index():
    if 'user_id' in session:  # Check if user is logged in
        user_id = session['user_id']
        message = request.args.get('message')
        
        # Fetch books associated with the logged-in user
        books = db.session.query(Book).filter(Book.user_id == user_id).all()
        
        return render_template('index.html', books=books, book=None, message=message)
    else:
        return redirect(url_for('login_page'))  # Redirect to login page if user is not logged in


@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    # Retrieve form data
    title = request.form['title']
    author = request.form['author']
    published_date_str = request.form['published_date']
    published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    isbn = request.form['isbn']
    num_pages = request.form['num_pages']
    cover_image_url = request.form['cover_image_url']
    genre = request.form['genre']
    publisher = request.form['publisher']
    language = request.form['language']
    description = request.form['description']
    ratings = request.form['ratings']
    user_id = session['user_id']  # Get the user ID from the session

    # Add the book to the database
    book = Book(
        title=title, author=author, published_date=published_date,
        isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url,
        genre=genre, publisher=publisher, language=language, description=description,
        ratings=ratings, user_id=user_id
    )
    db.session.add(book)
    db.session.commit()
    return redirect(url_for('index'))




@app.route('/update_book', methods=['POST'])
@login_required
def update_book():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    data = request.get_json()  # Get JSON data from request body
    book_id = data.get('book_id')  # Extract book_id from JSON data

    if book_id is None:
        return jsonify({'error': 'Book ID not provided'}), 400

    book = db.session.query(Book).filter(Book.id == book_id).first()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to update this book'}), 403

    # Retrieve form data
    title = data.get('title')
    author = data.get('author')
    published_date_str = data.get('published_date')
    isbn = data.get('isbn')
    num_pages = data.get('num_pages')
    cover_image_url = data.get('cover_image_url')
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

    # Commit changes to the database
    db.session.commit()

    # Return success response with updated book details
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


@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    book = db.session.query(Book).filter(Book.id == book_id).first()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    if book.user_id != session['user_id']:
        return jsonify({'error': 'You are not authorized to delete this book'}), 403

    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('index'))



# Define GraphQL queries
# class Query(ObjectType):
#     books = graphene.List(BookType)
#     book = graphene.Field(BookType, id=graphene.Int())
#     books_by_genre = graphene.List(BookType, genre=graphene.String())
   

#     def resolve_books(self, info):
#         return SessionLocal().query(Book).all()

#     def resolve_book(self, info, id):
#         return SessionLocal().query(Book).filter(Book.id == id).first()

#     def resolve_books_by_genre(self, info, genre):
#         return SessionLocal().query(Book).filter(Book.genre == genre).all()

    

class Query(ObjectType):
    reviews = graphene.List(ReviewType)
    users = graphene.List(UserType)
    def resolve_reviews(self, info):
        # Fetch and return all reviews from the database
        return db.session.query(Review).all()
    def resolve_users(self, info):
        # Fetch and return all users from the database
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
            # Fetch user and book objects from the database
            user = db.session.query(User).get(user_id)
            book = db.session.query(Book).get(book_id)

            # Validate user and book objects
            if not user:
                raise GraphQLError(f"User with ID {user_id} not found")
            if not book:
                raise GraphQLError(f"Book with ID {book_id} not found")

            # Create a new review object
            review = Review(
                user=user,
                book=book,
                rating=rating,
                comment=comment,
                timestamp=timestamp if timestamp else datetime.utcnow()
            )

            # Add the review to the database session and commit changes
            db.session.add(review)
            db.session.commit()

            return CreateReview(review=review)

class DeleteReview(graphene.Mutation):
        class Arguments:
            reviewId = graphene.Int(required=True)

        success = graphene.Boolean()

        def mutate(self, info, reviewId):
            # Attempt to fetch the review object
            review = db.session.query(Review).get(reviewId)

            # Check if review exists
            if not review:
                raise GraphQLError(f"Review with ID {reviewId} not found")

            # Delete the review
            db.session.delete(review)
            db.session.commit()

            # Return success
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

        # Update fields
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
# Define GraphQL mutations
class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()
    update_book = UpdateBook.Field()
    delete_book = DeleteBook.Field()
    create_review = CreateReview.Field()
    delete_review = DeleteReview.Field()
# Create GraphQL schema
schema = Schema(query=Query,mutation=Mutation)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)

# @app.route('/create_review', methods=['POST'])
# @login_required
# def create_review():
#     if 'user_id' not in session:
#         return jsonify({'error': 'User not logged in'}), 401

#     data = request.get_json()
#     user_id = data.get('user_id')
#     book_id = data.get('book_id')
#     rating = data.get('rating')
#     comment = data.get('comment')
#     timestamp = data.get('timestamp')

#     user = db.session.query(User).get(user_id)
#     book = db.session.query(Book).get(book_id)

#     if not user:
#         return jsonify({'error': f"User with ID {user_id} not found"}), 404
#     if not book:
#         return jsonify({'error': f"Book with ID {book_id} not found"}), 404

#     review = Review(
#         user=user,
#         book=book,
#         rating=rating,
#         comment=comment,
#         timestamp=timestamp if timestamp else datetime.utcnow()
#     )

#     db.session.add(review)
#     db.session.commit()

#     return jsonify({'success': 'Review created successfully'}), 200
# from flask_graphql_auth import AuthInfoField, create_access_token, query_jwt_required, mutation_jwt_required, get_jwt_identity, get_raw_jwt

# class CreateReview(graphene.Mutation):
#     class Arguments:
#         user_id = graphene.Int(required=True)
#         book_id = graphene.Int(required=True)
#         rating = graphene.Int(required=True)
#         comment = graphene.String()
#         timestamp = graphene.DateTime()

#     review = graphene.Field(ReviewType)

#     @mutation_jwt_required
#     def mutate(self, info, user_id, book_id, rating, comment=None, timestamp=None):
#         current_user_id = get_jwt_identity()  # Get the ID of the current user

#         # Validate rating
#         if not 1 <= rating <= 5:
#             raise GraphQLError("Rating must be between 1 and 5")

#         # Check if the current user matches the user_id provided in the arguments
#         if current_user_id != user_id:
#             raise GraphQLError("You are not authorized to leave a review for this user")

#         # Fetch user and book objects from the database
#         user = db.session.query(User).get(user_id)
#         book = db.session.query(Book).get(book_id)

#         # Validate user and book objects
#         if not user:
#             raise GraphQLError(f"User with ID {user_id} not found")
#         if not book:
#             raise GraphQLError(f"Book with ID {book_id} not found")

#         # Create a new review object
#         review = Review(
#             user=user,
#             book=book,
#             rating=rating,
#             comment=comment,
#             timestamp=timestamp if timestamp else datetime.utcnow()
#         )

#         # Add the review to the database session and commit changes
#         db.session.add(review)
#         db.session.commit()

#         return CreateReview(review=review)

# class DeleteReview(graphene.Mutation):
#     class Arguments:
#         review_id = graphene.Int(required=True)

#     success = graphene.Boolean()

#     @mutation_jwt_required
#     def mutate(self, info, review_id):
#         current_user_id = get_jwt_identity()  # Get the ID of the current user

#         # Fetch the review object
#         review = db.session.query(Review).get(review_id)

#         # Check if review exists
#         if not review:
#             raise GraphQLError(f"Review with ID {review_id} not found")

#         # Check if the current user matches the user who left the review
#         if current_user_id != review.user_id:
#             raise GraphQLError("You are not authorized to delete this review")

#         # Delete the review
#         db.session.delete(review)
#         db.session.commit()

#         # Return success
#         return DeleteReview(success=True)

