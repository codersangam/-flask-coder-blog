from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail
import json
import os, math
from werkzeug import secure_filename

with open('config.json', "r") as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.secret_key = 'the random string'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail_username'],
    MAIL_PASSWORD=params['gmail_password']
)
mail = Mail(app)
if local_server:
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:admin123@localhost:8080/coderblog'
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
db = SQLAlchemy(app)  # mysql initialization


class Contact(db.Model):
    '''serialnum, name, email, phone, message, date'''
    serialnum = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20), nullable=True)


class Posts(db.Model):
    serialnum = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(20), nullable=True)
    img_file = db.Column(db.String(20), nullable=True)
    tagline = db.Column(db.String(300), nullable=False)


@app.route('/')
def index():
    posts = Posts.query.filter_by().all()
    # [0:params['no_of_posts']]
    last = math.ceil(len(posts) / int(params['no_of_posts']))

    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[(page - 1) * int(params['no_of_posts']): (page - 1) * int(params['no_of_posts']) + int(
        params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)

    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"

    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route('/about')
def about():
    return render_template('about.html', params=params)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_username']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')
        if username == params['admin_username'] and password == params['admin_password']:
            # set the session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
    return render_template('login.html', params=params)


@app.route("/post/<string:post_slug>", methods=["GET"])
def samplepost(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route("/edit/<string:serialnum>", methods=["GET", "POST"])
def edit(serialnum):
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if serialnum == '0':
                post = Posts(serialnum=serialnum, title=box_title, tagline=tline, slug=slug, content=content,
                             img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
                flash("New Post has been added successfully..!", "success")

            else:
                post = Posts.query.filter_by(serialnum=serialnum).first()
                post.title = box_title
                post.tagline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                flash("Your Post has been updated successfully..!", "success")
                return redirect('/edit/' + serialnum)
        post = Posts.query.filter_by(serialnum=serialnum).first()
        return render_template('edit.html', params=params, post=post, serialnum=serialnum)


@app.route('/uploader', methods=["GET", "POST"])
def upload():
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "File Uploaded Successfully"


@app.route('/logout')
def logout():
    session.pop("user")
    return redirect("/dashboard")


@app.route('/delete/<string:serialnum>', methods=["GET", "POST"])
def delete(serialnum):
    if 'user' in session and session['user'] == params['admin_username']:
        post = Posts.query.filter_by(serialnum=serialnum).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == 'POST':
        '''add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contact(name=name, email=email, phone=phone, message=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message from ' + name,
                          sender=email,
                          recipients=[params['gmail_username']],
                          body=message + "\n" + phone
                          )
        flash("Thank you for contacting us. We will get you back soon..!", "success")
    return render_template('contact.html', params=params)


app.run(debug=True)
