from sqlalchemy import or_, and_, not_, asc, desc, func
from sqlalchemy.orm.exc import MultipleResultsFound
from datetime import datetime, timedelta

from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g, jsonify

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from flask_login import LoginManager, login_required, login_user, logout_user, current_user

from flaskext.markdown import Markdown

from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, IntegerField, HiddenField, SubmitField, validators, ValidationError, widgets

import db

app = Flask('translator')
Markdown(app)
app.config.from_pyfile("config.py")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.context_processor
def new_template_globals():
    def datetime_format(value, format='%d. %m. %Y %H:%M:%S'):
        if not value: return "-"
        if isinstance(value, str): return value
        return value.strftime(format)
    
    return {
        'type': type,
        'db': db,
        'datetime': datetime_format
    }



#app.jinja_env.globals['type'] = type
# XXX for some reason, doing this stops the Flask devserver from reloading
# templates.  bug?
#app.jinja_env.globals['db'] = db

# inspired by http://flask.pocoo.org/snippets/12/
def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash("Chyba u {}: {}".format(
                getattr(form, field).label.text,
                error
            ), 'danger')

@app.before_request
def before_request():
    g.sitename = app.config['SITENAME']
    g.db = db
    g.now = datetime.now()
    g.yesterday = g.now - timedelta(days=1)
    g.tomorrow = g.now + timedelta(days=1)

@app.teardown_request
def shutdown_session(exception=None):
    db.session.close()
    db.session.remove()

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(db.User).get(user_id)

@app.route("/")
def index():
    projects = db.session.query(db.Project).order_by(db.Project.position.asc()).all()
    
    return render_template("index.html", projects=projects)
    
@app.route("/<project_identifier>/<category_identifier>/")
def category(project_identifier, category_identifier):
    project = db.Project.from_identifier(project_identifier)
    if not project: abort(404)
    category = db.Category.from_identifier(category_identifier, project=project)
    if not category: abort(404)
    
    terms = db.session.query(db.Term).filter(db.Term.category == category,
        db.Term.hidden == False)
    
    return render_template("category.html", project=project, category=category,
        terms=terms)

class SuggestionForm(Form):
    text = TextField('Návrh', [validators.required()])
    description = TextField('Popis')
    submit = SubmitField('Přidat návrh')
    
class CommentForm(Form):
    comment_text = TextAreaField('Komentář', [validators.required()])
    submit = SubmitField('Přidat komentář')

@app.route("/<project_identifier>/<category_identifier>/<term_identifier>/",
    methods="GET POST".split())
def term(project_identifier, category_identifier, term_identifier):
    # XXX this is a horrible train, make it more concise
    project = db.Project.from_identifier(project_identifier)
    if not project: abort(404)
    category = db.Category.from_identifier(category_identifier, project=project)
    if not category: abort(404)
    try:
        term = db.Term.from_identifier(term_identifier, category=category)
    except MultipleResultsFound:
        return "Tomuto identifikátoru odpovídá více termínů.  Tohle je CHYBA a musí ji opravit administrátor.  Můžete pomoci tím že nahlásíte URL."
    if not term: abort(404)
    
    suggestion_form = None
    comment_form = None
    if current_user.is_authenticated and not term.locked:
        suggestion_form = SuggestionForm(request.form)
        comment_form = CommentForm(request.form)
        if request.method == 'POST' and suggestion_form.validate():
            suggestion_text = suggestion_form.text.data.strip()
            if db.session.query(db.Suggestion).filter(
                db.Suggestion.text == suggestion_text,
                db.Suggestion.term == term,
                (db.Suggestion.status == "approved")).all():
                # TODO this should check for "final" as well, but
                # for some reason adding `or (db.Suggestion.status == "final")`
                # doesn't cut it
                flash("Přesně tenhle návrh už existuje, mrkni se po něm!", 'info')
            else:
                suggestion = db.Suggestion(user=current_user, term=term,
                    created=datetime.now(), changed=datetime.now(),
                    text=suggestion_text, description=suggestion_form.description.data,
                    status="approved")
                
                db.session.add(suggestion)
                db.session.commit()
                return redirect(term)
        if request.method == 'POST' and comment_form.validate():
            comment = db.Comment(user=current_user, term=term,
                created=datetime.now(),
                text=comment_form.comment_text.data,
                deleted=False)
            
            db.session.add(comment)
            db.session.commit()
            return redirect(term)

    
    return render_template("term.html", project=project, category=category, term=term,
        suggestion_form=suggestion_form, comment_form=comment_form,
        vote_from_for = db.Vote.from_for)

@app.route("/recent")
def recent():
    
    suggestions = db.session.query(db.Suggestion).filter(db.Suggestion.status == "approved").order_by(db.Suggestion.created.desc()).limit(100).all()
    comments = db.session.query(db.Comment).filter(db.Comment.deleted == False).order_by(db.Comment.created.desc()).limit(100).all()
    
    changes = [c for c in suggestions + comments if c.created]
    changes.sort(key=lambda x: x.created, reverse=True)
    changes = changes[0:100]
    
    return render_template("recent.html", changes=changes)

@app.route("/users")
def users():
    users = db.session.query(db.User).filter(db.User.active == True).all()
    
    return render_template("users.html", users=users)

@app.route("/vote", methods=["POST"])
@login_required
def vote():
    suggestion = db.session.query(db.Suggestion).get(request.form['suggestion_id'])
    if not suggestion: abort(404)
    if suggestion.term.locked: abort(403)
    if suggestion.status not in ["approved"]:
        flash("Voting for a suggestion that isn't approved isn't possible.", 'danger')
        return redirect(suggestion.url)
    vote_num = request.form['vote']
    if vote_num not in ["0", "1", "2"]: abort(400)
    
    vote = db.Vote.from_for(current_user, suggestion)
    if vote:
        db.session.delete(vote)
    vote = db.Vote(suggestion=suggestion, user=current_user, vote=vote_num,
        valid=True, changed=datetime.now())
    db.session.add(vote)
    db.session.commit()
    
    if not request.is_xhr:
        return redirect(suggestion.url)
    else:
        return "OK"
    
@app.route("/suggestion", methods=["POST"])
@login_required
def suggestion():
    suggestion = db.session.query(db.Suggestion).get(request.form['suggestion_id'])
    if not suggestion: abort(404)
    if suggestion.term.locked: abort(403)
    action = request.form['action']
    if action in "delete approve hide".split():
        if current_user.admin:
            if action == 'delete':
                suggestion.status = 'deleted'
            elif action == 'approve':
                suggestion.status = 'approved'
            elif action == 'hide':
                suggestion.status = 'hidden'
        else:
            abort(403)
    
    if action == 'withdraw' and suggestion.user == current_user:
        if suggestion.score == 0:
            suggestion.status = 'withdrawn'
            flash("Návrh vzán zpět.", 'success')
        else:
            flash("Návrh lze vzít zpět pouze dokud má nulové skóre.", 'danger')
    
    db.session.commit()
    return redirect(suggestion.url)

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
                flash("Jste přihlášeni.", 'success')
                return redirect(url_for('index'))
            else:
                failed = True
    
    return render_template("login.html", form=form, failed=failed)

class RegisterForm(Form):
    username = TextField('Username', [validators.required()])
    password = PasswordField('Heslo', [
        validators.Required(),
        validators.EqualTo('confirm_password', message='Hesla se musí shodovat')
    ])
    confirm_password = PasswordField('Heslo znovu', [validators.required()])
    email = TextField('Email', [validators.required()])
    key = TextField('Klíč', [validators.required()])
    submit = SubmitField('Zaregistrovat se')

@app.route("/register", methods="GET POST".split())
def register():
    form = RegisterForm(request.form)
    failed = False
    if request.method == 'POST' and form.validate():
        if form.key.data != app.config["REGISTER_KEY"]:
            flash("Zadali jste nesprávný registrační klíč.", "danger")
        else:
            user = db.session.query(db.User).filter(db.User.username == form.username.data.lower()).scalar()
            if user:
                flash("Toto uživatelské jméno je již zabrané, vyberte si, prosím, jiné.", "danger")
            else:
                user = db.User(username=form.username.data.lower(),
                    email=form.email.data,
                    active=True,
                    registered=datetime.now(),
                    seen=datetime.now())
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                
                login_user(user, remember=True)
                flash("Registrace proběhla úspěšně.", 'success')
                return redirect(url_for('index'))
    else:
        flash_errors(form)
    
    return render_template("register.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def create_admin():
    admin = Admin(app)
    
    class RestrictedModelView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('login', next=request.url))
    
    for table in (db.User, db.Project, db.Category, db.Term, db.Suggestion, db.Comment, db.Outlink):
        admin.add_view(RestrictedModelView(table, db.session))


create_admin()

if __name__ == "__main__":
    app.run(host="", port=8004, debug=True, threaded=True)
