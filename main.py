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
# from flask_login import login_required, current_user
from flask_login import login_required,current_user
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
# from flask_wtf.csrf import CSRFProtect
# from flask_wtf.csrf import CSRFError
from flask import jsonify
from flask_jwt_extended import JWTManager,create_access_token,jwt_required, get_jwt_identity


app = Flask(__name__)
# csrf = CSRFProtect(app)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to a random secret key

# SQLALCHEMY_DATABASE_URL = "sqlite:///./books.db"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./books.db'
app.config['SECRET_KEY'] = '9494'
db = SQLAlchemy(app)
jwt = JWTManager(app)
# engine = create_engine(SQLALCHEMY_DATABASE_URL)
# engine = create_engine(app.config)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
login_manager = LoginManager(app)
login_manager.init_app(app)

class User(Base, UserMixin):
    __tablename__ = "user"  # <-- Update the table name to 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
      # Define relationship with books
    books = relationship("Book", back_populates="user")

# Define SQLAlchemy models
class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    published_date = Column(Date)
    isbn = Column(String, index=True)
    num_pages = Column(Integer)
    cover_image_url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'))  # Define user_id column and establish a ForeignKey relationship
    
    # Define relationship with User
    user = relationship("User", back_populates="books")
# migrate = Migrate(app, db)

# Define GraphQL types
class BookType(SQLAlchemyObjectType):
    class Meta:
        model = Book
        interfaces = (graphene.relay.Node,)
    id = graphene.ID(description="ID of the book", required=True)

    def resolve_id(self, info):
        return str(self.id)
    
# Create database tables
Base.metadata.create_all(bind=engine)

@login_manager.user_loader
def loader_user(user_id):
    return db.session.query(User).get(user_id)

with app.app_context():
    db.create_all()

        # session = SessionLocal()
# @app.route('/login', methods=["GET", "POST"])
# def login_page():
#     if request.method == "POST":
#         email = request.form.get("email")
#         password = request.form.get("password")
        
#         # Query the user from the database
#         user = db.session.query(User).filter_by(email=email).first()
        
#         if user and user.password == password:
#             session['user_id'] = user.id  # Store user id in session
#             return redirect(url_for("index", message="Login successful, welcome {}!".format(user.name)))  # Redirect to index page after login
            
#     return render_template('login.html')


@app.route('/login', methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = db.session.query(User).filter_by(email=email).first()
        
        if user and user.password == password:
            session['user_id'] = user.id
            access_token=create_access_token(identity=user.id)
            return{'access_token':access_token},200
        return {'messege':'Invalide'},401
    return render_template('login.html')

# Update register route
# @app.route('/register',methods=["GET", "POST"])
# def register_page():
#     if request.method=="POST":
#         user = User(email=request.form.get("email"),
#                     password=request.form.get("password"),
#                     name=request.form.get('name'))
#         db.session.add(user)
#         db.session.commit()
#         session['user_id'] = user.id  # Store user id in session
#         return redirect(url_for("index"))  # Redirect to book management page after registration
#     return render_template('register.html')

@app.route('/register', methods=["POST"])
def register_page():
    email = request.form.get("email")
    password = request.form.get("password")
    name = request.form.get('name')
    
    # Check if required fields are not None
    if email is None or password is None or name is None:
        return {'error': 'Missing required fields'}, 400

    # Check if email already exists
    if db.session.query(User).filter_by(email=email).first():
        return {'error': 'Email already exists'}, 409

    # Create the user
    user = User(email=email, password=password, name=name)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return {'message': 'User created successfully'}, 201




@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user id from session
    return redirect(url_for('index')) 

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Access protected resources
    current_user_id = get_jwt_identity()
    return {'user_id': current_user_id}, 200

# Update the index route
@app.route('/')
def index():
    if 'user_id' in session:  # Check if user is logged in
        message = request.args.get('message')
        books = SessionLocal().query(Book).all()
        return render_template('index.html', books=books, book=None, message=message)
    else:
        return redirect(url_for('login_page'))  # Redirect to login page if user is not logged in

# @app.route('/')
# def index():
#     books = SessionLocal().query(Book).all()
#     return render_template('index.html', books=books, book=None)

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    # Handle adding a new book
    # Retrieve form data
    title = request.form['title']
    author = request.form['author']
    published_date_str = request.form['published_date']
    published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
    isbn = request.form['isbn']
    num_pages = request.form['num_pages']
    cover_image_url = request.form['cover_image_url']
    user_id = current_user.id  
    # Add the book to the database
    db = SessionLocal()
    # user_id = session['user_id']
    book = Book(title=title, author=author, published_date=published_date,
                isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url, user_id=user_id)
    db.add(book)
    db.commit()
    return redirect(url_for('index'))


@app.route('/update_book', methods=['POST'])
@login_required
def update_book():
    db = SessionLocal()
    data = request.get_json()  # Get JSON data from request body
    book_id = data['book_id']  # Extract book_id from JSON data

    book = db.query(Book).filter(Book.id == book_id).first()
    # if book:
    if book and book.user_id == current_user.id: 
        # Retrieve form data
        title = data['title']
        author = data['author']
        published_date_str = data['published_date']
        isbn = data['isbn']
        num_pages = data['num_pages']
        cover_image_url = data['cover_image_url']

        # Validate and parse published_date
        published_date = datetime.strptime(published_date_str, '%Y-%m-%d') if published_date_str else None

        # Update the book
        book.title = title
        book.author = author
        book.published_date = published_date
        book.isbn = isbn
        book.num_pages = num_pages
        book.cover_image_url = cover_image_url

        db.commit()
        db.refresh(book)
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
                'cover_image_url': book.cover_image_url
            }
        }), 200
    else:
        return jsonify({'success': False, 'message': 'Book not found'}), 404

    return redirect(url_for('index')) # Respond with success status

   
@app.route('/delete_book/<int:book_id>', methods=['POST'])
# @login_required
def delete_book(book_id):
    # Handle deleting a book
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    # if book:
    if book and book.user_id == current_user.id:
        db.delete(book)
        db.commit()
    return redirect(url_for('index'))


# @app.errorhandler(CSRFError)
# def handle_csrf_error(e):
#     return render_template('csrf.html', reason=e.description), 400

# Define GraphQL queries
class Query(ObjectType):
    books = graphene.List(BookType)
    book = graphene.Field(BookType, id=graphene.Int())

    def resolve_books(self, info):
        return SessionLocal().query(Book).all()

    def resolve_book(self, info, id):
        return SessionLocal().query(Book).filter(Book.id == id).first()

class CreateBook(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        author = graphene.String()
        published_date = graphene.Date()
        isbn = graphene.String()
        num_pages = graphene.Int()
        cover_image_url = graphene.String()
    
    book = graphene.Field(BookType)

    def mutate(self, info, title, author, published_date, isbn, num_pages, cover_image_url):
        db = SessionLocal()
        book = Book(title=title, author=author, published_date=published_date,
                    isbn=isbn, num_pages=num_pages, cover_image_url=cover_image_url)
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

    book = graphene.Field(BookType)

    def mutate(self, info, id, title, author, published_date, isbn, num_pages, cover_image_url):
        db = SessionLocal()
        book=db.query(Book).filter(Book.id == id).first()
        if not book:
            raise Exception(f"Book with id {id} not found")

        if title:
            book.title = title
        if author:
            book.author = author
        if published_date:
            book.published_date = published_date
        if isbn:
            book.isbn = isbn
        if num_pages:
            book.num_pages = num_pages
        if cover_image_url:
            book.cover_image_url = cover_image_url

        db.commit()
        db.refresh(book)
        return UpdateBook(book=book)

class DeleteBook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    book = graphene.Field(BookType)
    def mutate(self,info,id):
        db = SessionLocal()
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

# Create GraphQL schema
schema = Schema(query=Query,mutation=Mutation)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

if __name__ == '__main__':
    app.run(debug=True)






# @app.route('/')
# def index():
#     message = request.args.get('message')
#     books = SessionLocal().query(Book).all()
#     return render_template('index.html', books=books, book=None,message=message)

# @app.route('/register',methods=["GET", "POST"])
# def register_page():
#     if request.method=="POST":
#         user = User(email=request.form.get("email"),
#                     password=request.form.get("password"),
#                     name=request.form.get('name'))
#         db.session.add(user)
#         db.session.commit()
#         login_user(user)  # Automatically login user after registration
#         return redirect(url_for("index"))  # Redirect to index route after registration
#     return render_template('register.html')

# @app.route('/login', methods=["GET", "POST"])
# def login_page():
#     if request.method == "POST":
#         email = request.form.get("email")
#         password = request.form.get("password")
        
#         # Query the user from the database
#         user = db.session.query(User).filter_by(email=email).first()
        
#         if user and user.password == password:
#             login_user(user)  # Login user
#             return redirect(url_for("index", message="Login successful, welcome {}!".format(user.name)))
#             # return redirect(url_for("index"))  # Redirect to index route after login
#     return render_template('login.html')


# @app.route('/logout')
# def logout():
#     logout_user()

#     return redirect(url_for("index"))