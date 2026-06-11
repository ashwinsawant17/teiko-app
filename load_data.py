import sqlite3
import csv


# creates the sqlite database in the given filename, creating it if necessary
def create_db(fname):
    """
    Creates the Database schema in the given filename.
    If a table already exists, it does not add it
    """

    # schemas, we'll prepend appropriate table creation commands later
    subjects_schema = """
    (
        subject VARCHAR(10) PRIMARY KEY,
        project VARCHAR(10),
        condition VARCHAR(20),
        age INT,
        sex CHAR(1),
        treatment VARCHAR(20),
        response BOOL
    )
    """

    samples_schema = """
    (
        sample VARCHAR(10) PRIMARY KEY,
        subject VARCHAR(10) REFERENCES subjects(subject),
        sample_type VARCHAR(10),
        time_from_treatment_start INT
    )
    """

    cell_counts_schema = """
    (
        sample VARCHAR(10) PRIMARY KEY REFERENCES samples(sample),
        b_cell INT,
        cd8_t_cell INT,
        cd4_t_cell INT,
        nk_cell INT,
        monocyte INT
    )
    """
    

    # decide the prepended table creation command based on the 
    # overwrite behavior if we decide to change it later on
    subjects_command = "CREATE TABLE IF NOT EXISTS subjects"

    samples_command = "CREATE TABLE IF NOT EXISTS samples"

    cell_counts_command = "CREATE TABLE IF NOT EXISTS cell_counts"


    # make the connection
    con = sqlite3.connect(fname)
    # enforce foreign keys
    con.execute("PRAGMA foreign_keys = ON")

    # CREATE THE CURSOR
    cur = con.cursor()

    # create the tables
    cur.execute(subjects_command + subjects_schema)
    cur.execute(samples_command + samples_schema)
    cur.execute(cell_counts_command + cell_counts_schema)

    # commit the changes and clean up
    con.commit()
    con.close()


def load_csv(csv_name, db_name):

    subject_insert = """
        INSERT INTO subjects (
            subject, project, condition, age, sex, treatment, response
        )
        VALUES (
            :subject,:project,:condition,:age,:sex,:treatment,:response
        )
    """

    sample_insert = """
        INSERT INTO samples (
            sample, subject, sample_type, time_from_treatment_start
        )
        VALUES (
            :sample,:subject,:sample_type,:time_from_treatment_start
        )
    """

    cell_counts_insert = """
        INSERT INTO cell_counts (
            sample, b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte
        )
        VALUES (
            :sample,:b_cell,:cd8_t_cell,:cd4_t_cell,:nk_cell,:monocyte
        )
    """

    # we will first parse the csv before inserting them all at once
    subjects = {}
    samples = []
    cell_counts = []

    with open(csv_name, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # add the subject into the subjects table ensuring uniquness
            subj_id = row['subject']
            if subj_id not in subjects:
                subjects[subj_id] = {
                    'subject': subj_id,
                    'project': row['project'],
                    'condition': row['condition'],
                    'age': int(row['age']),
                    'sex': row['sex'],
                    'treatment': row['treatment'],
                    'response': None if row['response'] is None else True if row['response'].strip().lower() == 'yes' else False,
                }
            
            # add in the sample data
            samples.append({
                'sample': row['sample'],
                'subject': subj_id,
                'sample_type': row['sample_type'],
                'time_from_treatment_start': int(row['time_from_treatment_start'])
            })

            # add in the cell count data
            cell_counts.append({
                'sample': row['sample'],
                'b_cell': int(row['b_cell']),
                'cd8_t_cell': int(row['cd8_t_cell']),
                'cd4_t_cell': int(row['cd4_t_cell']),
                'nk_cell': int(row['nk_cell']),
                'monocyte': int(row['monocyte'])
            })


    # make the connection
    con = sqlite3.connect(db_name)
    # enforce foreign keys
    con.execute("PRAGMA foreign_keys = ON")
    # CREATE THE CURSOR
    cur = con.cursor()

    # perform an execute many on each of our parsed data 'tables'
    cur.executemany(subject_insert, subjects.values())
    cur.executemany(sample_insert, samples)
    cur.executemany(cell_counts_insert, cell_counts)

    # commit the transaction and close
    con.commit()
    con.close()

def clean_db(db_name):
    con = sqlite3.connect(db_name)
    cur = con.cursor()

    # drop in this order to avoid foreign key constraints, 
    # although i technically don't set that in this connection lifetime
    cur.execute("DROP TABLE IF EXISTS cell_counts")
    cur.execute("DROP TABLE IF EXISTS samples")
    cur.execute("DROP TABLE IF EXISTS subjects")    

    con.commit()
    con.close()


if __name__ == "__main__":

    db_filename = "cell-count.db"
    csv_filename = "cell-count.csv"

    # first wipe the tables
    clean_db(db_filename)

    # then recreate the tables
    create_db(db_filename)

    # now load the csv data in
    load_csv(csv_filename, db_filename)