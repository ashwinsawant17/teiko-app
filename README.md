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
python dashboard.py
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
My brainstorming on schema design can be found [here](/notes.txt) or simply navigate to notes.txt in the root directory of this repository \
More specifically, though, I knew I wanted to separate subjects and the actual sample information. \
This could avoid unnecessary duplication of data unique to a specific subject, not to a sample. \
I then further decided to split up the sample data into metadata and cell counts. \
I imagined most queries would be performed on cell counts, but not necessarily on metadata

After this process, these are the commands I used to create the necessary tables \
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

CREATE TABLE cell_counts(
    sample VARCHAR(10) PRIMARY KEY REFERENCES samples(sample),
    b_cell INT,
    cd8_t_cell INT,
    cd4_t_cell INT,
    nk_cell INT,
    monocyte INT
)
```

`subjects` holds information pertaining to a single subject (project, condition, age, sex, treatment, etc) \
`samples` holds metadata pertaining to a single sample (sample type, time from treatment_start) \
`cell_counts` holds the raw cell counts for each cell populations

As mentioned earlier, we avoid duplication of data by separating on who owns the data (subject vs treatment) \
Splitting samples on cell counts and metadata keeps the actual sample information table narrow (cell_counts). Performing any sort of analysis on cell_counts, such as calculating relative frequencies requires less scanned data than if we were to include the metadata as well. \
The current scheme scales reasonably at larger scale, but as there are more projects, subjects, and samples there may be a few things I would change: \
Add a separate table for Projects. This is assuming more projects also comes with some additional metadata about them. \
It would be useful to not need to duplicate this information \
I'd also switch over to auto generated (probably integer) primary keys we could perform faster searches with as this table got very big \
For more analyses on different subject or sample populations (ex: Let's look at subjects within this specific age group, let's look at samples this many days after treatment) Indexing on common query columns like condition, treatment would speed up these queries

## Code Structure
load_data.py is fairly self explanatory. I have a function for creating the tables, a function for loading the csv data, and a function for clearing the tables \
This is primarily to allow me to experiment with schemas if need be, or experiment with insertion methods \
It also allows me to create tables and check schemas before I start loading in large datasets

analysis.py primarily splits up the functionality by section of Bob's analysis

1. `get_relative_frequencies`: get the relative frequencies 
2. `freq_on_response`: get them based on response (along with additional filtering)
3. `plot_responses`: plot the responses if need be 
4. `compute_statistics` compute the statistical significance using Mann Whitney U Test and a T Test. Requiring both to be more resistant to normality constraints (especially because it's a percentage that skews toward lower percentages)
5. `get_sig_pops`: actually retrieve which cell populations had significant difference between responders and non-responders
6. `subset_analysis`: perform the subset analysis that Bob wants, saving the results into csv files in the output directory

In general, I aim to make it as modular as possible, so that some of these functions can be reused in the later dashboard. For that same reason, a lot of the filtering that Bob does before doing his analysis, I input as optional parameters, so that we can later let a user make those choices themselves.

The dashboard is again split up by function. Essentially using those functions to display the analysis in a more interactive way, letting the user choose their filtering options. Because some of the displays rely on the same kind of filtering, I created a sidebar for the common ones, although they do not affect everything. This way a user doesn't have to choose between having to re-select their filtering choices (if we remade the selectors closer to the new insights) or having to scroll up and down to some common place where they choose the filtering.