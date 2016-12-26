from datetime import datetime

from unidecode import unidecode

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, String, Enum, Text, Boolean, TypeDecorator

import bcrypt

import config

import app
from flask import Flask, url_for
app = Flask('translator')
app.config.from_pyfile("config.py")

engine = create_engine(config.DATABASE, encoding="utf8", echo=config.DEBUG)

session = scoped_session(sessionmaker(bind=engine, autoflush=False))

Base = declarative_base(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255))
    email = Column(String(255))
    minipic_url = Column(String(255), default='')
    profile = Column(Text, default='')
    admin = Column(Boolean, nullable=False, default=False)
    
    
    def verify_password(self, password):
        if self.pass_.startswith('$2a'):
            return bcrypt.hashpw(password.encode('utf-8'), self.password.encode('utf-8')) == self.pass_
    
    def set_password(self, password):
        self.pass_ = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def __str__(self):
        return self.username

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    
    def __str__(self):
        return self.identifier

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship("Project", backref='categories')
    
    def url(self):
        return url_for('category', 
            project_identifier=self.project.identifier,
            category_identifier=self.identifier)
    
    def __str__(self):
        return self.project.identifier + '/' + self.identifier

class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, primary_key=True, nullable=False)
    number = Column(Integer)
    identifier = Column(String(255), nullable=False)
    label = Column(String(255))
    text_en = Column(Text)
    text_jp = Column(Text)
    
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", backref='terms')
    
    def __str__(self):
        return self.category.project.identifier + '/' + self.category.identifier \
            + "/" + self.identifier

class Suggestion(Base):
    __tablename__ = 'suggestions'
    
    id = Column(Integer, primary_key=True, nullable=False)
    text = Column(Text)
    description = Column(Text, default='')
    status = Column(Enum("new", "denied", "approved", "withdrawn", "final", "hidden", "deleted"))
    
    created = Column(DateTime)
    changed = Column(DateTime)
    
    term_id = Column(Integer, ForeignKey('terms.id'))
    term = relationship("Term", backref='suggestions')
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", backref='suggestions')

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True, nullable=False)
    text = Column(Text)
    created = Column(DateTime)
    deleted = Column(Boolean)
    
    term_id = Column(Integer, ForeignKey('terms.id'))
    term = relationship("Term", backref='comments')
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", backref='comments')

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)


















