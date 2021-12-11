import os
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, flash, redirect,
    url_for, session, request, logging)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from passlib.hash import sha256_crypt
from wtforms import (
    Form, StringField, TextAreaField, PasswordField, validators, FileField)
if os.path.exists("env.py"):
    import env

app = Flask(__name__)

# MongoDB Connection Config
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    all_articles = mongo.db.articles.find()
    return render_template('articles.html', articles=all_articles)


@app.route('/article/<page_id>')
def article(page_id):
    return render_template('article.html', id=page_id)


@app.route("/get_users")
def get_users():
    users = mongo.db.users.find()
    return render_template('users.html', users=users)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(
        min=4, max=25, message="Username must be between 4 and 25 characters.")
    ])
    email = StringField('Email', [
        validators.Length(min=6, max=35),
        validators.Regexp(
            '^[a-zA-Z0-9.!#$%&*+/=?_~-]+@[a-zA-Z0-9-]+(?:\\.[a-zA-Z0-9-]+)*$',
            message="Must be a valid e-mail")
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get('username').lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))
        # registration (requires an dictionary {} to store info)
        registration = {
            "name": request.form.get("name").lower(),
            "email": request.form.get("email").lower(),
            "username": request.form.get("username").lower(),
            "password": sha256_crypt.hash(request.form.get("password"))
        }
        # insert_one requires an dictionary to store info in mongoDB
        mongo.db.users.insert_one(registration)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration successful!", 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# User Log in
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = RegisterForm(request.form)
    if request.method == 'POST':
        # Check if user exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # Ensure hashed password matches user input
            if sha256_crypt.verify(
                request.form.get("password"), existing_user["password"]):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")), 'success')
# return redirect(url_for('profile', username=session["user"]))
                return redirect(url_for('articles'))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # Username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template('login.html', form=form)


# Check if user logged in (function decorator)
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please login!', 'danger')
            return redirect(url_for('login'))
    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


# Dashboard, for logged in users
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Get articles from db

    return render_template('dashboard.html')


# User Account form class
class UpdateAccountForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(
        min=4, max=25, message="Username must be between 4 and 25 characters.")
    ])
    email = StringField('Email', [
        validators.Length(min=6, max=35),
        validators.Regexp(
            '^[a-zA-Z0-9.!#$%&*+/=?_~-]+@[a-zA-Z0-9-]+(?:\\.[a-zA-Z0-9-]+)*$',
            message="Must be a valid e-mail")
    ])


# Profile Account page (for logged in users)
# @app.route("/account", methods=["GET", "POST"])
# def account():
#     # grab the session user's username from db
#     user = mongo.db.users.find_one(
#         {"username": session['user']})
#     user_image = url_for('static', filename='pics/userimage.jpg')
#     form = UpdateAccountForm(request.form)
#     if request.method == 'POST' and form.validate():
#         update_account = {
#                 "name": request.form.get("name").lower(),
#                 "email": request.form.get("email").lower(),
#                 "username": request.form.get("username").lower()
#             }
#         # insert_one requires an dictionary to store info in mongoDB
#         mongo.db.users.update(update_account)
#         return redirect(url_for('account'))
#     return render_template(
#         "account.html", user=user, user_image=user_image, form=form)


# Article form class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=100)])
    body = TextAreaField('Body', [
        validators.Length(min=10)], render_kw={'rows': 20})


# Category form class
class CategoryForm(Form):
    category = StringField('Category', [validators.Length(min=3, max=25)])


# Add article (to db)
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():

        one_article = {
            "title": request.form.get("title").lower(),
            "body": request.form.get("body").lower(),
            "author": session["user"],
            "create_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        mongo.db.articles.insert_one(one_article)
        flash('Article Created!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


# This is from the Code Institute walkthrough, might need some adjusting
@app.route("/edit_article/<article_id>", methods=["GET", "POST"])
@is_logged_in
def edit_task(article_id):
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():

        one_article = {
            "title": request.form.get("title").lower(),
            "body": request.form.get("body").lower(),
            "author": session["user"],
            "create_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        mongo.db.articles.update({"_id": ObjectId(article_id)}, one_article)
        flash('Article Successfully Updated!', 'success')

    article = mongo.db.articles.find_one({"_id": ObjectId(article_id)})

    all_articles = mongo.db.articles.find()
    return render_template(
        'edit_task.html', article=article, articles=all_articles)


@app.route("/delete_article/<article_id>")
def delete_article(article_id):
    mongo.db.articles.remove({"_id": ObjectId(article_id)})
    flash("Article successfully removed!")
    return redirect(url_for('articles'))


# Categories
@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route('/add_category', methods=["GET", "POST"])
@is_logged_in
def add_category():
    form = CategoryForm(request.form)
    if request.method == 'POST' and form.validate():

        one_category = {
            "category_name": request.form.get('category').lower(),
            "create_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        mongo.db.categories.insert_one(one_category)
        flash("Category Successfully Created!", 'success')
        return redirect(url_for('dashboard'))

    return render_template("add_category.html", form=form)


# Edit Category
@app.route("/edit_category/<category_id>", methods=["GET", "POST"])     #  route decorator which is passed with variable of category_id
@is_logged_in
def edit_category(category_id):
    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    form = CategoryForm(request.form, category)

    # populate category form fields
    form.category.data = category['category_name']

    if request.method == 'POST' and form.validate():

        one_category = {
            "category_name": request.form.get('category').lower(),
            "create_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        mongo.db.categories.update(
            {"_id": ObjectId(category_id)}, one_category)
        flash("Category Successfully Updated", 'success')
        return redirect(url_for('get_categories'))

    return render_template(
        "edit_category.html", form=form, category=category)


# Delete Category
@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully removed!")
    return redirect(url_for('get_categories'))


if __name__ == '__main__':
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
