# Cytometry Analysis for Teiko

## Build instructions
This project was developed assuming Python 3.12.3, though it should work on most modern Python versions
This project uses a PIP virtual environment. To create a virtual environment:
```
python -m venv .venv
```
Once the environment is created, we need to activate it. \
Depending on whether you're on windows or a Unix-derivative system, do one of the following \
Windows (assuming you are on CMD, but the directory is the same, the filename may just change):
```
.\.venv\Scripts\activate.bat
```
Linux / macOS:
```
source .venv/bin/activate
```
To install the necessary dependencies, go to the root directory and use the command:
```
pip install -r requirements.txt
```
You can then run load_data.py, analysis.py, and dashboard.py
```
python load_data.py
python analysis.py
python dahsboard.py
```

If you are using the given Makefile, you can bypass all of these steps, as it will create the virtual environment for you \
Use the setup target to install everything
```
make setup
```
Use the pipeline target to generate all the plots and tables
```
make pipeline
```
Use the dashboard target to run the dashboard
```
make dashboard
```

By default, you can find tables and plots in the `output/` directory

## Schema Design
My more brainstorming on schema design can be found [here](/notes.txt) 
More specifically, though, I knew I wanted to separate subjects and the actual sample information \
to avoid unecessary duplication of data unique to a specific subject, not to a sample \
I then further decided to split up the sample data into metadata and cell counts \
Since I imagined most queries would be performed on cell counts, but not necessarily on metadata \
It scales fairly well already, but as there are more projects, subjects, and samples there may be a few things I would change: \
Add a separate table for Projects. This is assuming more projects also comes with some additional metadata about them. \
It would be useful to not need to duplicate this information \
I'd also switch over to auto generated (probably integer) primary keys we could perform faster searches with as this table got very big \
These are the commands I used to create the necessary tables \
```
CREATE TABLE subjects(
    subject VARCHAR(10) PRIMARY KEY,
    project VARCHAR(10),
    condition VARCHAR(20),
    age INT,
    sex CHAR(1),
    treatment VARCHAR(20),
    response BOOL
)

CREATE TABLE samples(
    sample VARCHAR(10) PRIMARY KEY,
    subject VARCHAR(10) REFERENCES subjects(subject),
    sample_type VARCHAR(10),
    time_from_treatment_start INT
)
```

## Code Structure
load_data.py is fairly self explanatory. I have a function for creating the tables, a function for loading the csv data, and a function for clearing the tables \
This is primarily to allow me to experiment with schemas if need be, or experiment with insertion methods \
It also allows me to create tables and check schemas before I start loading in large datasets \

analysis.py primarily splits up the functionality by section of Bob's analysis