import os
import re
import requests

from flask import Flask, session, render_template, request, jsonify, redirect, url_for
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
app.config['JSON_SORT_KEYS'] = False

Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=['GET', 'POST'])
def login():
    if session['logged_in'] is True:
        return render_template('book_search.html', user=session['user'])
    session['id'] = []
    session['user'] = []
    session['logged_in'] = False
    msg = ''
    if request.method == 'POST' and 'user_name' in request.form and 'user_password' in request.form:
        username = request.form.get('user_name')
        password = request.form.get('user_password')
        account = db.execute('SELECT * FROM users WHERE user_name = :a AND user_password= :b',
                             {'a': username, 'b': password}).fetchone()
        db.commit()
        if account:
            session['logged_in'] = True
            session['id'] = account[0]
            session['user'] = account[1]
            return render_template('book_search.html', user=session['user'])
        else:
            msg = 'Incorrect username/password. Please, try again or register.'
    return render_template('index.html', msg=msg)


@app.route("/logout")
def logout():
    session['books'] = None
    session['user'] = None
    session['id'] = None
    session['logged_in'] = False
    return render_template('index.html', msg='You have logged out!')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if session['logged_in'] is True:
        return redirect(url_for('logout'))
    else:
        msg = ''
        if request.method == 'POST' and 'user_name' in request.form and 'email' in request.form and 'user_password' in request.form:
            username = request.form.get('user_name')
            session['user'] = username
            password = request.form.get('user_password')
            email = request.form.get('email')
            account = db.execute("SELECT * FROM users WHERE user_name = :a",
                             {'a': username}).fetchone()
            if account:
                msg = 'Account already exists'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = 'Username must contain only characters and numbers'
            elif not username or not password or not email:
                msg = 'Please fill out the form'
            else:
                db.execute("INSERT INTO users (user_name, user_password, email) VALUES "
                       "(:username, :password, :email)",
                       {'username': username, 'password': password, 'email': email})
                db.commit()
                msg = 'You have successfully registered! Please go back to Login page.'
        return render_template('register.html', msg=msg)


@app.route("/search", methods=['POST', 'GET'])
def search():
    if session['logged_in'] is True:
        session['books'] = []
        if 'text' in request.form and request.method == 'POST':
            query = f"%{request.form.get('text')}%"
            query1 = query.title()
            books = db.execute("SELECT isbn, title, author, year FROM books WHERE "
                               "isbn LIKE :query "
                               "OR title LIKE :query "
                               "OR title LIKE :query1 "
                               "OR author LIKE :query1 "
                               "OR author LIKE :query",
                               {'query': query, 'query1': query1}).fetchall()
            db.commit()
            if books:
                for book in books:
                    session['books'].append(book)
                return render_template('search_results.html', books=books, user=session['user'])
            else:
                return render_template('book_search.html', msg="Not found", user=session['user'])
    elif session['logged_in'] is False and request.method == 'GET':
        msg = 'Please login.'
        return render_template('index.html', msg=msg)


@app.route("/book/<string:isbn>", methods=['GET', 'POST'])
def result(isbn):
    if session['logged_in'] is True:
        session['reviews'] = []
        msg = ''
        review = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND user_name = :user_name",
                            {'isbn': isbn, 'user_name': session.get('user')}).fetchone()
        if review is None and request.method == 'POST':
            review = request.form.get('review')
            rate = request.form.get('rate')
            if review and rate:
                db.execute("INSERT INTO reviews (user_name, isbn, review, rate) VALUES "
                       "(:user_name, :isbn, :review, :rate)",
                       {'user_name': session.get('user'), 'isbn': isbn, 'review': review, 'rate': rate})
                msg = 'Success!'
            else:
                msg = 'You need to rate and write review.'
        elif review and request.method == 'POST':
            msg = 'Sorry. You may post only 1 review.'
        db.commit()
        key = "GA9MKDGCniczEgaRaEeQ"
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={'key': key, 'isbns': isbn})
        if res:
            average = res.json()['books'][0]['average_rating']
            count = res.json()['books'][0]['reviews_count']
        else:
            average = '0'
            count = '0'
        reviews = db.execute("SELECT user_name, review, rate FROM reviews WHERE isbn = :isbn",
                             {'isbn': isbn}).fetchall()
        for review in reviews:
            session['reviews'].append(review)
        books = db.execute('SELECT * FROM books WHERE isbn = :isbn',
                           {'isbn': isbn}).fetchone()
        db.commit()
        return render_template('book.html', books=books, average_rating=average, count=count, msg=msg,
                               reviews=session['reviews'], user=session['user'])
    elif session['logged_in'] is False or request.method == 'GET':
        msg = 'Please login.'
        return render_template('index.html', msg=msg)


@app.route("/book/api/<isbn>")
def book_api(isbn):
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn': isbn}).fetchone()
    if books is None:
        return jsonify({"error": "The book does not exist"}), 404
    count = db.execute("SELECT COUNT(review) FROM reviews WHERE isbn = :isbn", {'isbn': isbn}).fetchone()
    average_score = db.execute("SELECT AVG(rate) FROM reviews WHERE isbn = :isbn", {'isbn': isbn}).fetchone()
    rev_count = round(float(count[0]))
    avg_score = round(float(average_score[0]), 2)
    db.commit()
    return jsonify(
        dict(title=books.title, author=books.author, year=int(books.year), isbn=books.isbn, review_count=rev_count,
             average_score=avg_score))