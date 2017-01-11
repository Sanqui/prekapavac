from sys import argv
import csv

import db

path = argv[1]
project_identifier = argv[2]
category_identifier = argv[3]

project = db.Project.from_identifier(project_identifier)
if not project:
    print("No such project: {}".format(project_identifier))
category = db.Category.from_identifier(category_identifier, project=project)
if not category:
    print("Making new category {}".format(category_identifier))

    category = db.Category(identifier=category_identifier,
        name=category_identifier, project=project)

    db.session.add(category)

with open(path) as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        if not row[0]: continue
        suggestions = []
        comments = []
        if len(row) == 3:
            num, en, jp = row
        else:
            num, en, jp, s1, s2, s3, s4, c1, c2 = row
            suggestions += [s1, s2, s3, s4]
            comments += [c1, c2]
        
        if not en: continue
        
        term = db.Term(number=num,
            identifier=en.lower().replace(' ', '-'),
            text_en=en, text_jp=jp,
            category=category)
        db.session.add(term)
        
        for s in suggestions:
            if s:
                suggestion = db.Suggestion(text=s,
                    status='approved',
                    term=term)
                db.session.add(suggestion)
        
        for c in comments:
            if c:
                comment = db.Comment(text=c,
                    term=term)
                db.session.add(comment)

db.session.commit()
