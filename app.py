from sqlalchemy import or_, and_, not_, asc, desc, func
from datetime import datetime

from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from flask_login import LoginManager, login_required, login_user, logout_user, current_user

from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, IntegerField, HiddenField, SubmitField, validators, ValidationError, widgets

import db

app = Flask('translator')
app.config.from_pyfile("config.py")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.before_request
def before_request():
    g.sitename = app.config['SITENAME']
    g.db = db

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
    
    return render_template("category.html", project=project, category=category)

class SuggestionForm(Form):
    text = TextField('Návrh', [validators.required()])
    description = TextField('Návrh', [validators.required()])
    submit = SubmitField('Přidat návrh')
    
class CommentForm(Form):
    comment_text = TextField('Návrh', [validators.required()])
    submit = SubmitField('Přidat komentář')

@app.route("/<project_identifier>/<category_identifier>/<term_identifier>/",
    methods="GET POST".split())
def term(project_identifier, category_identifier, term_identifier):
    # XXX this is a horrible train, make it more concise
    project = db.Project.from_identifier(project_identifier)
    if not project: abort(404)
    category = db.Category.from_identifier(category_identifier, project=project)
    if not category: abort(404)
    term = db.Term.from_identifier(term_identifier, category=category)
    if not term: abort(404)
    
    #suggestions = db.session.query(db.Suggestion, func.sum(db.Vote.vote).label("score")).join(db.Vote) \
    #    .filter(db.Suggestion.term==term, db.Suggestion.status in "new approved final".split(),
    #    ).order_by("score").all()
    #suggestions = db.session.query(db.Suggestion) \
    #    .filter(db.Suggestion.term==term, db.Suggestion.status == "approved").all()
    
    suggestion_form = None
    comment_form = None
    if current_user.is_authenticated:
        suggestion_form = SuggestionForm(request.form)
        comment_form = CommentForm(request.form)
        if request.method == 'POST' and suggestion_form.validate():
            suggestion_text = suggestion_form.text.data.strip()
            if db.session.query(db.Suggestion).filter(db.Suggestion.text == suggestion_text, db.Suggestion.term == term).all():
                flash("Přesně tenhle návrh už existuje, mrkni se po něm!")
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

@app.route("/vote", methods=["POST"])
@login_required
def vote():
    suggestion = db.session.query(db.Suggestion).get(request.form['suggestion_id'])
    if not suggestion: abort(404)
    if suggestion.status not in ["approved"]:
        flash("Voting for a suggestion that isn't approved isn't possible.")
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
    
    return redirect(suggestion.url)
    
@app.route("/suggestion", methods=["POST"])
@login_required
def suggestion():
    suggestion = db.session.query(db.Suggestion).get(request.form['suggestion_id'])
    if not suggestion: abort(404)
    action = request.form['action']
    if current_user.admin:
        if action == 'delete':
            suggestion.status = 'deleted'
        elif action == 'approve':
            suggestion.status = 'approved'
        elif action == 'hide':
            suggestion.status = 'hidden'
    else:
        abort(403)
    
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
    
    class RestrictedModelView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('login', next=request.url))
    
    for table in (db.User, db.Project, db.Category, db.Term, db.Suggestion, db.Comment):
        admin.add_view(RestrictedModelView(table, db.session))


if __name__ == "__main__":
    create_admin()
    app.run(host="", port=8004, debug=True, threaded=True)
