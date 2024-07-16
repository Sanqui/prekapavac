import typing
from app import app
import db

with app.app_context():
    fixed_count = 0
    terms: typing.List[db.Term] = db.session.query(db.Term).filter(db.Term.dialogue == True).all()

    for term in terms:
        suggestions = db.session.query(db.Suggestion).filter(db.Suggestion.term == term).order_by(db.Suggestion.created.asc()).all()
        for i, suggestion in enumerate(suggestions):
            if suggestion.revision != i + 1:
                suggestion.revision = i + 1
                db.session.add(suggestion)
                fixed_count += 1
    
    print(f"Fixing {fixed_count} revisions...")

    db.session.commit()