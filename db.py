from datetime import datetime
import math
import enum

from unidecode import unidecode

from sqlalchemy import create_engine, func, and_, or_, case, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, String, Enum, Text, Boolean, TypeDecorator
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from flask_sqlalchemy import SQLAlchemy

import bcrypt

import config

from flask import Flask, url_for
#app = Flask('translator')
#app.config.from_pyfile("config.py")

#QUALITY_MIN = app.config.get("QUALITY_MIN", 1)

if 'mysql' in config.DATABASE:
    engine = create_engine(config.DATABASE, encoding="utf8", pool_size = 100, pool_recycle=4200, echo=config.DEBUG) # XXX
    # pool_recycle is to prevent "server has gone away"
else:
    engine = create_engine(config.DATABASE, encoding="utf8", echo=config.DEBUG)

db = SQLAlchemy()

session = db.session # scoped_session(sessionmaker(bind=engine, autoflush=False))

Base = db.Model # declarative_base(bind=engine)

class WithIdentifier():
    @classmethod
    def from_identifier(cls, identifier, **params):
        return session.query(cls).filter(cls.identifier==identifier).filter_by(**params).scalar()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255))
    email = Column(String(255))
    minipic_url = Column(String(255), default='')
    profile = Column(Text, default='')
    admin = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    
    registered = Column(DateTime)
    seen = Column(DateTime)
    
    @property
    def influence(self):
        suggestion_conditions = (
            Term.locked == False,
            Term.hidden == False,
            Suggestion.HAS_GOOD_STATUS
        )
        
        rated_count = session.query("Vote") \
            .select_from(Suggestion) \
            .join("votes") \
            .join(Term) \
            .filter(
                Vote.user == self,
                Vote.valid == True,
                *suggestion_conditions
            ).count()
        
        count = session.query(Suggestion).join(Term).filter(
            *suggestion_conditions
        ).count()
        
        return rated_count / count
    
    def verify_password(self, password):
        if self.password.startswith('$2b'):
            return bcrypt.hashpw(password.encode('utf-8'), self.password.encode('utf-8')) == self.password.encode('utf-8')
        else:
            raise ValueError("unknown password format")
    
    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    @property
    def is_authenticated(self): return True
    
    @property
    def is_active(self): return self.active
    
    @property
    def is_anonymous(self): return False
    
    def get_id(self):
        return str(self.id)
    
    def __str__(self):
        return self.username
    
def count_global_suggestions(rated_by=None):
    suggestion_conditions = (
        Term.locked == False,
        Term.hidden == False,
        Suggestion.HAS_GOOD_STATUS
    )
    
    if not rated_by:
        count = session.query(Suggestion) \
            .join(Term) \
            .filter(
                *suggestion_conditions
        ).count()
    
    else:
        count = session.query("Vote") \
            .select_from(Suggestion) \
            .join("votes") \
            .join(Term) \
            .filter(
                Vote.user == rated_by,
                Vote.valid == True,
                *suggestion_conditions
            ).count()
    
    return count

class Project(Base, WithIdentifier):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    position = Column(Integer)
    
    categories = relationship("Category", order_by="Category.position")
    
    def count_suggestions(self, rated_by=None):
        suggestion_conditions = (
            Term.locked == False,
            Term.hidden == False,
            Suggestion.HAS_GOOD_STATUS
        )
        
        if not rated_by:
            count = session.query(Suggestion) \
                .join(Term) \
                .join(Category) \
                .filter(
                    Category.project_id == self.id,
                    *suggestion_conditions
            ).count()
        
        else:
            count = session.query("Vote") \
                .select_from(Suggestion) \
                .join("votes") \
                .join(Term) \
                .join(Category) \
                .filter(
                    Vote.user == rated_by,
                    Vote.valid == True,
                    Category.project_id == self.id,
                    *suggestion_conditions
                ).count()
        
        return count
    
    @property
    def url(self):
        return url_for('index', _anchor=self.identifier)
    
    def __str__(self):
        return self.identifier

class Category(Base, WithIdentifier):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    position = Column(Integer)
    hidden = Column(Boolean, nullable=False, default=False)
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    project = relationship("Project", order_by=position)
    
    @property
    def link_outlinks(self):
        return session.query(Outlink).filter(Outlink.category==self,
            Outlink.type == "link").all()
        
    @property
    def icon(self):
        return session.query(Outlink).filter(Outlink.category==self,
            Outlink.type == "icon").scalar()
    
    @property
    def url(self):
        return url_for('category', 
            project_identifier=self.project.identifier,
            category_identifier=self.identifier)
    
    @property
    def mainly_dialogue(self):
        terms = session.query(Term).filter(
            Term.hidden == False,
            Term.category == self)
        
        dialogue_terms = terms.filter(Term.dialogue == True)
        
        ratio = dialogue_terms.count() / terms.count()
        return ratio >= 0.5
    
    def count_suggestions(self, rated_by=None):
        suggestion_conditions = (
            Term.category == self,
            Term.locked == False,
            Term.hidden == False,
            Suggestion.HAS_GOOD_STATUS
        )
        
        if not rated_by:
            count = session.query(Suggestion).join(Term).filter(
                *suggestion_conditions
            ).count()
        
        else:
            count = session.query("Vote") \
                .select_from(Suggestion) \
                .join("votes") \
                .join(Term) \
                .filter(
                    Vote.user == rated_by,
                    Vote.valid == True,
                    *suggestion_conditions
                ).count()
        
        return count
    
    def __str__(self):
        if self.project:
            return self.project.identifier + '/' + self.identifier
        else:
            return "???" + '/' + self.identifier

class ReferenceType(enum.Enum):
    #reference = 0
    mention = 1
    speaker = 2
    location = 3
    context = 4

class Reference(Base):
    __tablename__ = 'references'
    
    id = Column(Integer, primary_key=True, nullable=False)
    term0_id = Column(Integer, ForeignKey('terms.id'))
    term1_id = Column(Integer, ForeignKey('terms.id'))
    
    type = Column(Enum(ReferenceType, name="reference_type"))
    
    valid = Column(Boolean, default=True, nullable=False)
    
    term0 = relationship("Term", foreign_keys=[term0_id])
    term1 = relationship("Term", foreign_keys=[term1_id])
    
    def __str__(self):
        return "{} {} {}".format(self.term0, "references" if self.valid else "does not reference", self.term1)

class Term(Base, WithIdentifier):
    __tablename__ = 'terms'

    id = Column(Integer, primary_key=True, nullable=False)
    number = Column(Integer)
    identifier = Column(String(255), nullable=False)
    label = Column(String(255))
    text_en = Column(Text)
    text_jp = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.id'))
    hidden = Column(Boolean, default=False, nullable=False)
    locked = Column(Boolean, default=False, nullable=False)
    lock_reason = Column(Text)
    
    dialogue = Column(Boolean, default=False, nullable=False)
    
    category = relationship("Category", backref='terms')
    
    #references = relationship("Reference", foreign_keys=[Reference.term0_id], order_by="Reference.id")
    
    comments = relationship("Comment", order_by="Comment.created")
    
    def references_of_type(self, of_type=None):
        if of_type == None:
            of_type = or_(Reference.type == ReferenceType.reference, Reference.type == None)
        else:
            of_type = (Reference.type == getattr(ReferenceType, of_type))
        return session.query(Reference).filter( \
            Reference.term0_id == self.id, Reference.valid == True,
            of_type) \
            .order_by(Reference.id).all()
    
    @property
    def references(self):
        return self.references_of_type()
            
    def referenced_of_type(self, of_type=None):
        if of_type == None:
            of_type = or_(Reference.type == ReferenceType.reference, Reference.type == None)
        else:
            of_type = (Reference.type == getattr(ReferenceType, of_type))
        return session.query(Reference).filter( \
            Reference.term1_id == self.id, Reference.valid == True,
            of_type) \
            .order_by(Reference.id).all()
    
    @property
    def referenced(self):
        return self.referenced_of_type()
    
    def suggestions_w_score_by_status(self, has_good=True):
        if self.dialogue:
            return self.revisions_w_score.all()
        return session.query(Suggestion, func.sum(Vote.vote).label('score')) \
            .filter(Suggestion.term==self, \
            Suggestion.HAS_GOOD_STATUS if has_good else "") \
            .outerjoin(Vote).group_by(Suggestion) \
            .order_by(case(value=Suggestion.status, whens=Suggestion.STATUS_ORDERING).desc(),
            text('score DESC')).all()
    
    @property
    def suggestions_w_score(self):
        return self.suggestions_w_score_by_status(True)
        
    @property
    def all_suggestions_w_score(self):
        return self.suggestions_w_score_by_status(False)
    
    @property
    def revisions_w_score(self):
        return session.query(Suggestion, func.sum(Vote.vote).label('score')) \
            .filter(Suggestion.term==self, \
            Suggestion.HAS_GOOD_STATUS) \
            .outerjoin(Vote).group_by(Suggestion).order_by(text('revision DESC'))
    
    @property
    def final_suggestion(self):
        s = session.query(Suggestion) \
            .filter(Suggestion.term==self, Suggestion.status=="final").first()
        return s
    
    @property
    def latest_revision(self):
        rev = session.query(Suggestion) \
            .filter(Suggestion.term==self) \
            .outerjoin(Vote).group_by(Suggestion).order_by(text('revision DESC')).first()
        return rev
    
    @property
    def potentially_referenced(self):
        terms = session.query(Term).join(Category).join(Project).filter( \
            func.replace(Term.text_en, "\n", " ")\
                .ilike("%"+self.text_en+"%"), \
            Term.id != self.id, \
            Term.hidden == False, \
            Category.hidden == False, \
            Project.id == self.category.project_id
            ).all()
        # XXX I still don't know enough SQL to do this properly.
        for ref in session.query(Reference).filter(Reference.term1_id == self.id):
            if ref.term0 in terms:
                terms.remove(ref.term0)
        
        return terms
    
    def user_has_unrated(self, user):
        if self.locked:
            # Locked Terms behave as if they had no suggestions
            return False
        for suggestion, score in self.suggestions_w_score:
            if not Vote.from_for(user, suggestion):
                return True
        return False
    
    @property
    def prev(self):
        return session.query(Term).filter(Term.category == self.category) \
            .filter(Term.number < self.number,
            Term.hidden == False) \
            .order_by(Term.number.desc()).first()
            
    @property
    def next(self):
        return session.query(Term).filter(Term.category == self.category) \
            .filter(Term.number > self.number,
            Term.hidden == False) \
            .order_by(Term.number.asc()).first()
    
    def __str__(self):
        if self.category:
            return str(self.category) \
                + "/" + self.identifier
        else:
            return "???" \
                + "/" + self.identifier
    
    @property
    def url(self):
        return url_for('term', 
            project_identifier=self.category.project.identifier,
            category_identifier=self.category.identifier,
            term_identifier=self.identifier)
    
class SuggestionStatus(enum.Enum):
    new = 1
    denied = 2
    approved = 3
    withdrawn = 4
    final = 5
    hidden = 6
    deleted = 7
    candidate = 8

class Suggestion(Base):
    __tablename__ = 'suggestions'
    
    id = Column(Integer, primary_key=True, nullable=False)
    text = Column(Text)
    description = Column(Text, default='')
    status = Column(Enum(SuggestionStatus, name="suggestion_status"))
    revision = Column(Integer)
    
    created = Column(DateTime)
    changed = Column(DateTime)
    
    term_id = Column(Integer, ForeignKey('terms.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    term = relationship("Term", backref='suggestions')
    user = relationship("User", backref='suggestions')
    
    GOOD_STATUSES = [SuggestionStatus.approved, SuggestionStatus.candidate, SuggestionStatus.final]
    HAS_GOOD_STATUS = or_(status == SuggestionStatus.approved,
        status == SuggestionStatus.candidate,
        status == SuggestionStatus.final)
    STATUS_ORDERING = {
        'deleted': 0, 
        'hidden': 1, 'withdrawn': 1,
        'denied': 1,
        'approved': 2, 'new': 2,
        'candidate': 3,
        'final': 4
    }
    
    @property
    def sorted_votes(self):
        votes = session.query(Vote) \
            .filter(Vote.suggestion == self,
                Vote.valid == True) \
            .order_by(
                case(value=Vote.user_id, whens={self.user_id: 1}).desc(),
                Vote.vote.desc(),
                Vote.changed.desc()
            ).all()
        return votes
    
    @property
    def score(self):
        score = session.query(
            func.sum(Vote.vote).label('score')).filter(
            Vote.suggestion == self and Vote.valid == True).scalar() or 0
        return score
    
    @property
    def negative_score(self):
        score = session.query(Vote).filter(
            Vote.suggestion == self and Vote.valid == True,
            Vote.vote == 0).count() or 0
        return score
    
    @property
    def conflicts(self):
        return session.query(Suggestion).filter(
            Suggestion.id != self.id,
            Suggestion.text == self.text,
            Suggestion.HAS_GOOD_STATUS
        )
    
    @property
    def quality(self):
        quality = 0
        total = 0
        people = 0
        for vote in self.votes:
            if vote.valid:
                influence = vote.user.influence
                if vote.vote < 2:
                    quality += influence * vote.vote
                    total += influence
                else:
                    quality += influence * 2
                    total += influence * 2
                people += 1
        
        if people >= QUALITY_MIN:
            return quality / total
        else:
            return None
    
    @property
    def url(self):
        return self.term.url
    
    def __str__(self):
        return "from {}, suggestion {}".format(self.user, self.text)

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True, nullable=False)
    text = Column(Text)
    created = Column(DateTime)
    deleted = Column(Boolean)
    
    term_id = Column(Integer, ForeignKey('terms.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    term = relationship("Term")
    user = relationship("User", backref='comments')
    
    def __str__(self):
        return "from {}, comment {}".format(self.user, self.text[0:16])

class Vote(Base):
    __tablename__ = 'votes'
    
    suggestion_id = Column(Integer, ForeignKey('suggestions.id'), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True, nullable=False)
    vote = Column(Integer, nullable=False)
    valid = Column(Boolean)
    
    suggestion = relationship("Suggestion", backref='votes')
    user = relationship("User", backref='votes')
    
    changed = Column(DateTime)
    
    @classmethod
    def from_for(cls, user, suggestion):
        return session.query(cls).filter(cls.user == user,
            cls.suggestion == suggestion).scalar()
    
    def __str__(self):
        return "on {}, {} vote from {}".format(self.suggestion.text, self.vote, self.user)
    
class Outlink(Base):
    __tablename__ = 'outlinks'
    id = Column(Integer, primary_key=True, nullable=False)
    label = Column(String(255))
    url = Column(String(255))
    category_id = Column(Integer, ForeignKey('categories.id'))
    type = Column(Enum("link", "image", "icon", name="outlink_type"))
    
    category = relationship("Category", backref='outlinks')
    
    def filled_url(self, term):
        return self.url.format(**{
            'term': term.text_en,
            'en': term.text_en,
            'en_lower': term.text_en.lower(),
            'en_lowercase': term.text_en.lower(),
            'en_capitalized': term.text_en.capitalize(),
            'en_title': term.text_en.title(),
            'jp': term.text_jp,
            'num': term.number,
            'number': term.number})
    
    def __str__(self):
        return "{}/{} {}".format(self.category, self.type, self.label)
    

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)


















