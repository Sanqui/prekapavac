from sys import argv
import csv

import db

path = argv[1]
category_identifier = argv[2]

category = db.Category(identifier=category_identifier,
    name=category_identifier)

db.session.add(category)

with open(path) as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        num, en, jp, s1, s2, s3, s4, c1, c2 = row
        term = db.Term(number=num,
            identifier=en.lower().replace(' ', '-'),
            text_en=en, text_jp=jp,
            category=category)
        db.session.add(term)
        
        for s in (s1, s2, s3, s4):
            if s:
                suggestion = db.Suggestion(text=s,
                    status='approved',
                    term=term)
                db.session.add(suggestion)
        
        for c in (c1, c2):
            if c:
                comment = db.Comment(text=c,
                    term=term)
                db.session.add(comment)

db.session.commit()
