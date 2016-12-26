from sqlalchemy import or_, and_, not_, asc, desc, func
from datetime import datetime

from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g
from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, IntegerField, HiddenField, SubmitField, validators, ValidationError, widgets

import db

app = Flask('translator')

@app.route("/")
def index():
    projects = db.session.query(db.Project).all()
    
    return render_template("index.html", projects=projects)


if __name__ == "__main__":
    app.run(host="", port=8004, debug=True, threaded=True)
