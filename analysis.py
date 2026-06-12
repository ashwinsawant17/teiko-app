import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, ttest_ind


# PART 2: Relative Frequencies
def get_relative_frequencies(source, output_path=None):
    # the query to get the necessary db info
    # we're going to (for now) keep it simple here and do the more interesting processing in pandas
    
    # if passed in source is a string, assume it's a path to the cell-count db
    if isinstance(source, str):
        query = "SELECT * from cell_counts"

        # create the database connection
        con = sqlite3.connect(source)

        # read the query data into a dataframe using pandas built in read_sql_query function
        df = pd.read_sql_query(query, con)

        # close the db connection, don't think we need a commit here since we're only reading data
        con.close()
    
    # if the passed in source isn't a string, assume it's a dataframe
    else:
        df = source

    

    # now actually perform the analysis with pandas
    cell_columns = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    # get the total counts
    df['total_count'] = df[cell_columns].sum(axis=1)

    # pivot (or i guess technically unpivot) it so that each row has its own cell type
    df = df.melt(id_vars=['sample', 'total_count'], value_vars=cell_columns, var_name='population', value_name='count')
    
    # now compute the percentages for each cell type
    df['percentage'] = (df['count'] / df['total_count']) * 100

    # let's save this data as a csv
    if (output_path is not None):
        df.to_csv(output_path)

    # TODO: maybe display it to console when this runs?
    # print(df.to_string())

    # return the summary table to use it for later analysis
    return df

# PART 3: Statistical Analysis 
def freq_on_response(dbname, condition=None, treatment=None, sample_type=None):
    # get the queries for those with a response, and those without
    query = """
        SELECT cc.* 
        FROM samples s
        JOIN subjects sub ON sub.subject = s.subject
        JOIN cell_counts cc ON s.sample = cc.sample
        WHERE sub.response = ?
            AND sub.condition = COALESCE(?, sub.condition)
            AND sub.treatment = COALESCE(?, sub.treatment)
            AND s.sample_type = COALESCE(?, s.sample_type)
        
    """

    # open connection to dbname
    con = sqlite3.connect(dbname)

    # dataframe for those who did have a response
    yes_df = pd.read_sql_query(query, con, params=(1, condition, treatment, sample_type))
    # print(yes_df.head(10))
    # dataframe for those who didn't have a response
    no_df = pd.read_sql_query(query, con, params=(0, condition, treatment, sample_type))
    # print(no_df.head(10))
    # technically speaking, response can be null if treatment can be anything, so we will account for that here
    # represents those that did not receive treatment, or otherwise have no response data
    query = query.replace("sub.response = ?", "sub.response IS ?")
    null_df = pd.read_sql_query(query, con, params=(None, condition, treatment, sample_type))

    # get the relative frequencies for each response condition
    yes_freq = get_relative_frequencies(yes_df)
    no_freq = get_relative_frequencies(no_df)
    null_freq = get_relative_frequencies(null_df)

    return yes_freq, no_freq, null_freq

def plot_responses(yes_freq, no_freq, output_path='output/cell_freq_response.png'):
    cell_cols = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    fix, axes = plt.subplots(nrows=1, ncols=len(cell_cols), figsize=(20, 4))

    freq_dict = {}

    for cell_type in cell_cols:
        yes_vals = yes_freq[yes_freq['population'] == cell_type]['percentage']
        no_vals = no_freq[no_freq['population'] == cell_type]['percentage']
        freq_dict[cell_type] = {
            'yes': yes_vals,
            'no': no_vals
        }
        
    
    maximum = max(yes_freq['percentage'].max(), no_freq['percentage'].max())
    
    for ax, cell_type in zip(axes, cell_cols):
        ax.set_ylim(0, maximum)
        ax.boxplot(
            [freq_dict[cell_type]['yes'], freq_dict[cell_type]['no']],
            tick_labels=['Responder', 'Non-responder']
        )
        ax.set_title(cell_type)
        ax.set_ylabel('Relative Frequency')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def compute_statistics(yes_freq, no_freq):
    cell_cols = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    stat_dict = {
        'ttest': {},
        'mwutest': {}
    }

    for cell_type in cell_cols:
        yes_vals = yes_freq[yes_freq['population'] == cell_type]['percentage']
        no_vals = no_freq[no_freq['population'] == cell_type]['percentage']

        _, m_pval = mannwhitneyu(yes_vals, no_vals)
        _, t_pval = ttest_ind(yes_vals, no_vals)
        stat_dict['ttest'][cell_type] = t_pval
        stat_dict['mwutest'][cell_type] = m_pval

    return stat_dict

def get_sig_pops(stat_dict, alpha=0.05, require_both=True):
    cell_cols = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    significant = []
    for cell in cell_cols:
        mwu_sig = stat_dict['mwutest'][cell] < alpha
        t_sig = stat_dict['ttest'][cell] < alpha
        if (require_both and (mwu_sig and t_sig)) or (not require_both and (mwu_sig or t_sig)):
            significant.append(cell)
    
    return significant

# PART 4: Subset Analysis
def subset_analysis(dbname, condition=None, treatment=None, sample_type=None, time_treatment=None, write_results=False, output_dir=None):

    if (write_results and output_dir is None):
        raise Exception("No output directory given to write into")
        

    # I'm not entirely sure if the project wants us to do indivdual queries for each, 
    # but for now im going have a base query and filter as need be in pandas
    query_4_1 = """
        SELECT sub.project, sub.subject, sub.sex, sub.response, sam.time_from_treatment_start, cc.*
        FROM subjects sub
        JOIN samples sam ON sub.subject = sam.subject
        JOIN cell_counts cc ON sam.sample = cc.sample
        WHERE sub.condition = COALESCE(?, sub.condition)
        AND sub.treatment = COALESCE(?, sub.treatment)
        AND sam.sample_type = COALESCE(?, sam.sample_type)
        AND sam.time_from_treatment_start = COALESCE(?, sam.time_from_treatment_start)
    """

    # get the filtered dataframe
    con = sqlite3.connect(dbname)
    df = pd.read_sql_query(query_4_1, con, params=(condition, treatment, sample_type, time_treatment))
    con.close()

    # optionally write the filtered data
    if (write_results):
        df['sample'].to_csv(f"{output_dir}/4_1.csv")

    # now that we've filtered it, extend the query as listed
    stats = {}

    # 4.2.1: how many samples from each project
    stats['samples_in_project'] = df.groupby('project')['sample'].nunique()
    if (write_results):
        stats['samples_in_project'].to_csv(f"{output_dir}/4_2_1.csv")

    # 4.2.2: how many subjects were responders/non-responders
    stats['response_status'] = df.drop_duplicates('subject')['response'].value_counts()
    if (write_results):
        stats['response_status'].to_csv(f"{output_dir}/4_2_2.csv")
    
    # 4.2.3 how many subjects were males/females
    stats['sex_status'] = df.drop_duplicates('subject')['sex'].value_counts()
    if (write_results):
        stats['sex_status'].to_csv(f"{output_dir}/4_2_3.csv")
    
    stats['male_responders_at_0'] = df[(df['sex'] == 'M') & (df['response'] == 1) & (df['time_from_treatment_start'] == 0)].drop_duplicates('sample')
    stats['avg_b_cells_male_responders'] = stats['male_responders_at_0']['b_cell'].mean()
    if (write_results):
        stats['male_responders_at_0'].to_csv(f"{output_dir}/4_2_4.csv")


    return stats



if __name__ == "__main__":
    dbname = "cell-count.db"

    # part 2
    df = get_relative_frequencies(dbname, "output/relative_freq.csv")

    # part 3
    yes_freq, no_freq, null_freq = freq_on_response(
        'cell-count.db', 
        condition='melanoma', 
        treatment='miraclib', 
        sample_type='PBMC'
    )

    plot_responses(yes_freq, no_freq)

    stat_dict = compute_statistics(yes_freq, no_freq)
    alpha = 0.05
    significant = get_sig_pops(stat_dict, alpha, require_both=True)
    print(significant)

    
    # part 4 subset analysis
    stats = subset_analysis(
        'cell-count.db',
        condition='melanoma',
        treatment='miraclib',
        sample_type='PBMC',
        time_treatment=0,
        write_results=True,
        output_dir='./output'    
    )

    print(stats['avg_b_cells_male_responders'])
