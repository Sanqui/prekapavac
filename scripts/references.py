from sys import argv
import csv
from tqdm import tqdm

import sys
import app
db = app.db

with app.app.app_context():
    def export():
        f = open('references.csv', 'w')
        writer = csv.writer(f)
        terms =  db.session.query(db.Term).join(db.Category).join(db.Project).filter( \
            db.Term.hidden == False, \
            db.Category.hidden == False, \
            ).order_by(db.Term.id)
        
        term_count = terms.count()
        
        writer.writerow("term1_id,term0_id,term1_identifier,term0_identifier,term1,term0,valid".split(","))
        for term1 in tqdm(terms, total=term_count):
            for term0 in term1.potentially_referenced:
                if not term1.text_en.strip(): continue
                if not term0.text_en.strip(): continue
                writer.writerow((term1.id, term0.id,
                    str(term1), str(term0),
                    term1.text_en, term0.text_en, 1))

        f.close()
    
    def import_():
        f = open('references.csv', 'r')
        reader = csv.reader(f)
        next(reader)
        for row in tqdm(reader):
            if not len(row): continue
            term1_id, term0_id, \
              term1_identifier, term0_identifier,\
              term1_text, term0_text, valid = row
            existing_refs = db.session.query(db.Reference).filter_by(term0_id=term0_id, term1_id=term1_id)
            for existing_ref in existing_refs:
                db.session.delete(existing_ref)
            
            reference = db.Reference(term0_id=term0_id, term1_id=term1_id, valid=int(valid))
            db.session.add(reference)
            db.session.commit()
    
    {"export": export, "import": import_}[sys.argv[1]]()
    
