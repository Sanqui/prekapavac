from sqlalchemy import or_, and_, not_, asc, desc, func
from datetime import datetime

from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from flask_login import LoginManager, login_required, login_user, logout_user

from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, IntegerField, HiddenField, SubmitField, validators, ValidationError, widgets

import db

app = Flask('translator')
app.config.from_pyfile("config.py")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(db.User).get(user_id)

@app.route("/")
def index():
    projects = db.session.query(db.Project).all()
    
    return render_template("index.html", projects=projects)
    
@app.route("/<project_identifier>/<category_identifier>/")
def category(project_identifier, category_identifier):
    project = db.Project.from_identifier(project_identifier)
    if not project: abort(404)
    category = db.Category.from_identifier(category_identifier, project=project)
    if not category: abort(404)
    
    return render_template("category.html", project=project, category=category)

@app.route("/<project_identifier>/<category_identifier>/<term_identifier>/")
def term(project_identifier, category_identifier, term_identifier):
    # XXX this is a horrible train, make it more concise
    project = db.Project.from_identifier(project_identifier)
    if not project: abort(404)
    category = db.Category.from_identifier(category_identifier, project=project)
    if not category: abort(404)
    term = db.Term.from_identifier(term_identifier, category=category)
    if not term: abort(404)
    
    
    return render_template("term.html", project=project, category=category, term=term)

class LoginForm(Form):
    username = TextField('Username', [validators.required()])
    password = PasswordField('Heslo', [validators.required()])
    submit = SubmitField('Přihlásit se')

@app.route("/login", methods="GET POST".split())
def login():
    form = LoginForm(request.form)
    failed = False
    if request.method == 'POST' and form.validate():
        user = db.session.query(db.User).filter(db.User.username == form.username.data.lower()).scalar()
        if not user: failed = True
        else:
            password_matches = user.verify_password(form.password.data)
            if password_matches:
                login_user(user, remember=True)
                flash("Jste přihlášeni.")
                return redirect(url_for('index'))
            else:
                failed = True
    
    return render_template("login.html", form=form, failed=failed)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def create_admin():
    admin = Admin(app)
    for table in (db.User, db.Project, db.Category, db.Term, db.Suggestion, db.Comment):
        admin.add_view(ModelView(table, db.session))


if __name__ == "__main__":
    create_admin()
    app.run(host="", port=8004, debug=True, threaded=True)
