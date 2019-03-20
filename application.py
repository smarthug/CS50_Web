import os
import requests

from flask import Flask, session , render_template , request , redirect ,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))



@app.route("/")
def index():
    if not session.get('logged_in'):
        return render_template("login_register.html")
    else:
        return render_template("search.html")
    


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    print( name , email , username , password)

    session["user_id"] = username

    db.execute("INSERT INTO users (name , email, username , password) VALUES (:name, :email, :username, :password)" ,
        {"name":name, "email":email, "username":username, "password":password})
    db.commit()
    return render_template("login_register.html")



@app.route("/login" , methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    user = db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username , "password":password})
    if user is None:
        return render_template("error.html", message="No such user or wrong password.")

    
    session['logged_in'] = True
    session['user_id'] = username
        
    return index()


@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['user_id'] = None

    return index()


@app.route("/search" , methods=["GET" , "POST"])
def search():
    search = request.form.get("search")
    print(search)
    newsearch = '%' + search + '%'
    books = db.execute("SELECT * FROM books WHERE isbn::text LIKE :search OR  title::text LIKE :search OR  author::text LIKE :search " , {"search" : newsearch})
    print(books)
    #books= [1,2,3]
    return render_template('search.html', books=books)



@app.route("/book/<string:isbn>")
def book(isbn):

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn" , {"isbn" : isbn}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn" , {"isbn" : isbn}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "rVnBIHaIh3RN7KTzjojxA", "isbns": isbn})
    goodreads=res.json()
    print(goodreads['books'])
    goodreads_book=goodreads['books'][0]
    return render_template('book.html', book=book , reviews=reviews, goodreads_book=goodreads_book)



@app.route("/review/<string:user_id>" , methods=["GET" , "POST"])
def review(user_id):
    isbn = request.form.get("isbn")
    rating = request.form.get("rating")
    review = request.form.get("review")
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn" , {"isbn" : isbn}).fetchone()


    user = db.execute("SELECT * FROM reviews WHERE isbn=:isbn AND user_id=:user_id" , {"isbn":isbn,"user_id":user_id }).fetchone()

    if user is None :
        db.execute("INSERT INTO reviews (isbn , user_id ,title , rating ,review) VALUES (:isbn,:user_id ,:title,:rating ,:review)" ,
            {"isbn":book.isbn,"user_id":user_id ,"title":book.title,"rating":rating ,"review":review})
        db.commit()
        return redirect('/book/'+isbn)

    

    db.commit()
    #book = db.execute("SELECT * FROM books WHERE isbn = :isbn" , {"isbn" : isbn}).fetchone()
    return 'You can sumbit your review only once'



@app.route("/api/<string:isbn>")
def api(isbn):
    """Return details about a single flight."""
    # Make sure flight exists.
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn" , {"isbn" : isbn}).fetchone()
    if book is None:
        return jsonify({"error 404": "Invalid ISBN"}), 404

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "rVnBIHaIh3RN7KTzjojxA", "isbns": isbn})
    goodreads=res.json()
    goodreads_book=goodreads['books'][0]

    

    return jsonify({
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "review_count":goodreads_book['work_ratings_count'],
            "average_score":goodreads_book['average_rating']
        })