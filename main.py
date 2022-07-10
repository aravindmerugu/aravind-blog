import smtplib
import ssl
from datetime import datetime
import gunicorn

import bleach
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

OWN_EMAIL = 'aravindkucet@gmail.com'
OWN_PASSWORD = 'kfrumxkqvedzgvao'
context = ssl.create_default_context()

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


# db.create_all()

# CREATE TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Comments(db.Model):
    __tablename__ = "user_comments_table"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)

# db.create_all()

# Line below only required once, when creating DB.
# db.create_all()

## strips invalid tags/attributes
def strip_invalid_html(content):
    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']

    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }

    cleaned = bleach.clean(content,
                           tags=allowed_tags,
                           attributes=allowed_attrs,
                           strip=True)

    return cleaned


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)

@app.route('/my_posts')
def my_posts():
    if current_user.is_authenticated:
        myposts = BlogPost.query.filter_by(author=current_user.name).all()
        return render_template("my-posts.html", all_posts=myposts)
    else:
        return ("<h1>Go back and please login</h1>")


@app.route("/post/<int:post_id>",methods=["POST", "GET"])
def show_post(post_id):
    commentform = CommentForm()
    if commentform.validate_on_submit():
        if current_user.is_authenticated:
            name = current_user.name
        else:
            name = 'anonymus'
        new_comment = Comments(
            post_id = post_id,
            text = commentform.comment.data,
            name = name
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    requested_post = BlogPost.query.get(post_id)
    comments = Comments.query.filter_by(post_id=post_id).all()
    return render_template("post.html", post=requested_post, commentform=commentform, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    success = ''
    if request.method == "POST":
        success = 'Email sent successfully'
        data = request.form
        send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True, success=success)
    return render_template("contact.html", msg_sent=False, success=success)


def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls(context=context)
        connection.login(OWN_EMAIL, OWN_PASSWORD)
        connection.sendmail(OWN_EMAIL, OWN_EMAIL, email_message)


@app.route("/new-post", methods=["GET", "POST"])
@login_required
def add_new_post():
    new_blog_post = CreatePostForm()
    if new_blog_post.validate_on_submit():
        new_post = BlogPost(
            title=new_blog_post.title.data,
            subtitle=new_blog_post.subtitle.data,
            date=datetime.now().strftime("%B %d, %Y"),
            body=strip_invalid_html(new_blog_post.body.data),
            author=current_user.name,
            img_url=new_blog_post.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=new_blog_post)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", index=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route('/register', methods=["GET", "POST"])
def register():
    new_user = RegisterForm()
    if new_user.validate_on_submit():
        if User.query.filter_by(email=new_user.email.data).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            new_user.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=new_user.email.data,
            password=hash_and_salted_password,
            name=new_user.username.data,

        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html", form=new_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Email exists and password correct
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
