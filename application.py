import os
import requests
from flask import Flask, session,render_template,flash, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__,static_url_path='/static')

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


#Used to look for books
def searchforBooks(str):
      return db.execute("SELECT * FROM books WHERE title LIKE '%"+str+"%' or  author LIKE '%"+str+"%' or  isbn LIKE '%"+str+"%';").fetchall()

#used to looke for a book and its reviews
def searchBookReview(str):
      book = db.execute("SELECT * FROM books WHERE isbn = '"+str+"';").fetchall()
      reviews = db.execute("SELECT * FROM reviews WHERE isbn = '"+str+"';").fetchall()
      return book, reviews

def checkRating(reviews):
    if len(reviews) > 0:
        rating = 0
        for review in reviews :
            rating += review.rating
        rating = rating / len(reviews)
        return rating
    else:
        return 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logout")
def logout():
    # Get form information.
    username = session["current"][0]
    password = session["current"][1]
    db.execute("UPDATE users SET logged = '0' WHERE username = :username AND password = :password", {"username": username, "password": password})
    db.commit()
    return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/registerUser", methods=["POST"])
def registerUser():
    #register
    # Get form information.
    username = request.form.get("username")
    password = request.form.get("password")
      
    # does user already exist
    if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount > 0:
        flash("Account exists! forgot password?")
        return register()
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
            {"username": username, "password": password})
    db.commit()
    flash("Account Created!")
    return register()

@app.route("/login", methods=["POST"])
def login():
    #login

    # Get form information.
    username = request.form.get("username")
    password = request.form.get("password")
      
    # does user exist
    if db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount > 0:
        db.execute("UPDATE users SET logged = '1' WHERE username = :username AND password = :password", {"username": username, "password": password})
        db.commit()
        
        session["current"] = []
        session["current"].append(username)
        session["current"].append(password)
        return redirect(url_for('search'))
    flash("Password or user incorrect.")
    return index()

@app.route("/search", methods = ["GET","POST"])
def search():
    results = 0
    if request.method ==  "POST":     
        search_data = request.form.get("search_data")
        results = searchforBooks(search_data)
    return render_template("bookSearch.html", results = results)

@app.route("/search/<string:isbn>", methods = ["GET"])
def search_book(isbn):
    book, reviews = searchBookReview(isbn)
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "izGF0r8Ku4FfD5GvX9d1w", "isbns": isbn})
    if len(book) == 0:
        return render_template('404.html'), 404
    return render_template("book.html", book = book[0], reviews = reviews, isbn = isbn, res = res.json()['books'][0])

@app.route("/review/<string:ISBN>", methods = ["GET"])
def review(ISBN):
    book, reviews = searchBookReview(ISBN)
    return render_template("newReview.html", isbn = ISBN,book=book[0])

@app.route("/subReview/<string:ISBN>", methods=["POST"])
def reviews(ISBN):
    # Get form information.
    username = session["current"][0]
    isbn = ISBN
    rating = request.form.get("rating")
    review = request.form.get("review")
    # check if user already has a review here to make a new or update an old review
    if db.execute("SELECT * FROM reviews WHERE username = :username AND isbn = :isbn", {"username": username, "isbn": isbn}).rowcount == 0:
        db.execute("INSERT INTO reviews (isbn, username, rating, review) VALUES (:isbn, :username, :rating, :review)",
            {"username": username, "isbn": isbn, "rating": rating, "review":review})
        db.commit()
        flash("New review created")
    else:
        db.execute("UPDATE reviews SET rating = :rating, review = :review WHERE username = :username AND isbn = :isbn", {"username": username, "isbn": isbn, "rating": rating, "review":review})
        db.commit()
        flash("Your review has been updated")
    book, reviews = searchBookReview(ISBN)
    return render_template("newReview.html", isbn = ISBN,book=book[0])

@app.route("/api/<string:isbn>", methods = ["GET"])
def apiBook(isbn):
    book, reviews = searchBookReview(isbn)
    if len(book) == 0:
        return render_template('404.html'), 404
    else :
        book = book[0]
        json_res = {
        "title": book.title,
        "author": book.author,
        "year": int(book.year),
        "isbn": book.isbn,
        "review_count": len(reviews),
        "average_score": checkRating(reviews)
        }
        return json_res, 200

