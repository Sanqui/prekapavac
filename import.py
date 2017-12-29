from sys import argv
import csv

DIALOGUE = True
LOCKED = True
COMMIT = False
SPEAKER_CATEGORY = "_speakers"

import app
db = app.db

def make_identifier(string):
    return string.lower().replace(' ', '-').replace('"', '')

with app.app.app_context():

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
    
    if DIALOGUE:
        speaker_category = db.Category.from_identifier(SPEAKER_CATEGORY, project=project)
        if not speaker_category:
            print("Making new speaker_category {}".format(SPEAKER_CATEGORY))

            speaker_category = db.Category(identifier=SPEAKER_CATEGORY,
                name=SPEAKER_CATEGORY, project=project,
                hidden=True)

    with open(path) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row[0]: continue
            suggestions = []
            comments = []
            speaker = None
            if len(row) == 3:
                num, en, jp = row
            elif DIALOGUE and len(row) == 4:
                num, en, jp, speaker = row
                speaker = speaker.lower().strip()
            else:
                num, en, jp, s1, s2, s3, s4, c1, c2 = row
                suggestions += [s1, s2, s3, s4]
                comments += [c1, c2]
            
            if not en: continue
            
            identifier = make_identifier(en)
            if DIALOGUE:
                identifier = str(num)
            
            term = db.Term(number=num,
                identifier=identifier,
                text_en=en, text_jp=jp,
                category=category,
                dialogue=DIALOGUE,
                locked=LOCKED)
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
            
            if speaker:
                if "/" in speaker:
                    print("TODO assuming {} is just {}".format(speaker, speaker.split("/")[-1]))
                    speaker = speaker.split("/")[-1]
                    
                s = db.session.query(db.Term).join(db.Category) \
                    .filter(db.Category.project == category.project,
                    db.Term.identifier == speaker).scalar()
                if not s:
                    print("Unknown speaker {}, adding".format(speaker))
                    s = db.Term(number=-1,
                        identifier=speaker,
                        text_en=speaker, text_jp=None,
                        category=speaker_category,
                        dialogue=False,
                        locked=True)
                    db.session.add(s)
                
                ref = db.Reference(term0=term, term1=s,
                    valid=True, type="speaker")
                db.session.add(ref)
    
    if COMMIT:
        db.session.commit()
        print("Committed")
    else:
        print("Didn't commit - dry run")
