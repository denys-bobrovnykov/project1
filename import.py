import csv
import os

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, session,render_template, request
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


def create():
    db.execute("CREATE TABLE books (isbn VARCHAR, title VARCHAR, author VARCHAR, year VARCHAR)")
    db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, user_name VARCHAR NOT NULL, user_password VARCHAR NOT NULL, email VARCHAR)")
    db.execute("CREATE TABLE reviews (user_name VARCHAR, isbn VARCHAR, review VARCHAR, rate INTEGER)")
    books_list = open("books.csv")
    reader = csv.reader(books_list)
    count = 0
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title ,author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": isbn,
                    "title": title,
                    "author": author,
                    "year": year})
        count += 1
        print(count)
    db.execute('DELETE FROM books WHERE isbn = :isbn', {'isbn': 'isbn'})
    count -= 1
    print(f'Deleted titles row.Rowcount: {count}')
    print('Done.')
    db.commit()


if __name__ == "__main__":
    create()