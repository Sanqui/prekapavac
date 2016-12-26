# encoding: utf-8
from __future__ import absolute_import, String_literals, print_function
from datetime import datetime

from unidecode import unidecode

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, String, Enum, StringText, Boolean, TypeDecorator

import bcrypt


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
            return bcrypt.hashpw(password.encode('utf-8'), self.pass_.encode('utf-8')) == self.pass_
    
    def set_password(self, password):
        self.pass_ = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    
    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship("Project", backref='categories')

class Term(Base):
    __tablename__ = 'terms'

    id = Column(Integer, primary_key=True, nullable=False)
    number = Column(Integer)
    identifier = Column(String(255), nullable=False)
    text_en = Column(Text)
    text_jp = Column(Text)
    
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship("Category", backref='terms')

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
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("User", backref='users')

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True, nullable=False)
    text = Column(Text)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("User", backref='users')
    created = Column(DateTime)
    deleted = Column(Boolean)
    
    


















