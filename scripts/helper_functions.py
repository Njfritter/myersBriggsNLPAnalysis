#!/usr/bin/env python3

################################################################
# Myers Briggs Personality Type Tweets Natural Language Processing
# By Nathan Fritter
# Project can be found at: 
# https://www.inertia7.com/projects/109 & 
# https://www.inertia7.com/projects/110
################################################################

##################
# Import packages
##################
import matplotlib as mpl
mpl.use('TkAgg') # Need to do this everytime for some reason
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re, nltk, string
from nltk.corpus import stopwords
import wordcloud
import os, sys
from multiprocessing import cpu_count, Pool
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.pipeline import Pipeline


# Confirm we are in the correct directory, otherwise break script 
# and prompt user to move to correct directory
filepath = os.getcwd()
if not filepath.endswith('myersBriggsNLPAnalysis'):
    print('\nYou do not appear to be in the correct directory,\
    you must be in the \'myersBriggsNLPAnalysis\' directory\
    in order to run these scripts. Type \'pwd\' in the command line\
    if you are unsure of your location in the terminal.')
    sys.exit(1)

##########################################
# DEFINE VARIABLES FOR TEXT PRE-PROCESSING
##########################################

columns = np.array(['type', 'posts'])

'''
Specific parsing strategy from:
https://marcobonzanini.com/2015/03/09/mining-twitter-data-with-python-part-2/
It involves treating mentions, retweets, hashtags, as their own entity
Feel free to change the code below as necessary if you want to try new things
'''

# This will be an attempt to tokenize emoticons into their own tokens
emoticons_str = r'''
    (?:
        [:=;] # Eyes
        [oO\-]? # Nose (optional)
        [D\)\]\(\]/\\OpPd] # Mouth
    )'''

# Everything else Twitter related
regex_str = [
    emoticons_str,
    r'<[^>]+>', # HTML tags
    r'(?:@[\w_]+)', # @-mentions
    r'(?:\#+[\w_]+[\w\'_\-]*[\w_]+)', # hashtags
    r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+', # URLS
    r'(?:(?:\d+,?)+(?:\.?\d+)?)', # Numbers 
    r'(?:[a-z][a-z\'\-_]+[a-z])', # Words with dashes (-) and apostrophes (')
    r'(?:[\w_]+)', # Other words
    r'(?:\S)' # Anything else?
]

# Compile the above string patterns into two tokenizers
# VERBOSE allows spaces in regex to be ignored, IGNORECASE will catch both lower and uppercase
# https://docs.python.org/3.4/library/re.html#re.verbose
token_re = re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
emoticon_re = re.compile(r'^' + emoticons_str + '$', re.VERBOSE | re.IGNORECASE)

#########################################################
# FUNCTIONS WE WILL BE USING/IMPORTING INTO OTHER SCRIPTS
#########################################################

def remove_stopwords(text):
    '''
    Purpose: Remove english stopwords, punctuation, and any manually declared stopwords

    Inputs:
    - text: tokenized string data to parse

    Returns:
    - clean_words: list of words with stopwords removed
    '''
    # Try finding the corpus of stopwords first to avoid trying a download again
    # Then make list of stopwords here so we don't do this every time this script is called
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
    stop_list = stopwords.words('english') + list(string.punctuation)

    clean_words = [term for term in text if term not in stop_list]
    return clean_words
    
def check_emoticons(tokens, lowercase = False):
    '''
    Purpose: Check if there is any emoticon in the word, skip lowercasing

    Inputs:
    - tokens: tokenized strings (from 'tokenize_data' function)

    Returns:
    - tokens: tokenized strings with emoticon casing preserved
    '''
    if lowercase:
        tokens = [token if emoticon_re.search(token) else token.lower() for token in tokens]
    return tokens

def tokenize_data(df, filter_stopwords = False):
    '''
    Purpose: Tokenize data according to strategy coded above

    Inputs:
    - df: Pandas dataframe containing at least one text column to be tokenized

    Returns:
    - token_df: Pandas dataframe with text column containing lists of tokenized strings

    NOTE: Here I am making a list, appending the values to the list, and turning into a dataframe
    Rather than appending dataframes to each other every iteration as that is not as efficient
    '''
    # Create empty list for results and conversion to DataFrame later
    token_list = []

    for idx, row in df.iterrows():

        # Split tweets into individual tweets
        tweets_split = row['posts'].split('|||')

        # Grab personality type since we're analyzing one row of data at a time
        #ptype = pd.Series(row['type'], name = 'type')
        ptype = row['type']

        # Iterate through list of tweets for each user
        for tweet in tweets_split:

            # Tokenize data
            tokenized_tweets = [token for token in token_re.findall(tweet)]

            # Check for emoticons so we don't lowercase them
            tokenized_tweets = check_emoticons(tokenized_tweets)

            # Remove stopwords if declared
            if filter_stopwords:

                tokenized_tweets = remove_stopwords(tokenized_tweets)

            # Append to list
            token_list.append([ptype, tokenized_tweets])

        # Print progress, as this step takes a while
        if idx % 100 == 0:
            print('Row %s of %s done' % (idx, df.shape[0]))

    token_df = pd.DataFrame(token_list, columns = columns, dtype = object)
    return token_df

def build_pipeline(vectorizer, tfidf, kbest, model):
    '''
    Purpose: Combine different parts of a machine learning model together
    
    Inputs:
    - vectorizer: count vectorizer object to handle n-gram instances
    - tfidf: Term Frequency Inverse Document Frequency object (common NLP technique)
    - chi2: feature selection object using chi-squared analysis
    - clf: machine learning classifier object (scikit-learn)

    Returns:
    - text_clf: a machine learning classifier object for training and evaluation
    '''
    text_clf = Pipeline([
        ('vect', vectorizer),
        ('tfidf', tfidf),
        ('chi2', kbest),
        ('clf', model),
    ])

    return text_clf

def grid_search(clf, parameters, jobs, X, y):  
    '''
    Purpose: Run parameter tuning in parallel

    Inputs:
    - clf: machine learning classifier object (scikit-learn)
    - parameters: grid of parameters and possible values to choose from
    - jobs: number of CPUs to utilize on machine (use -1 for all CPUs)
    - X: attributes of data
    - y: response variable of data
    '''
    gs_clf = GridSearchCV(clf, 
    param_grid = parameters, 
    n_jobs = jobs,
    verbose = 7
    )
    gs_clf = gs_clf.fit(X, y)

    best_parameters, score, _ = max(gs_clf.grid_scores_, key = lambda x: x[1])
    for param_name in sorted(parameters.keys()):
        print("%s: %r" % (param_name, best_parameters[param_name]))
    print(score)

    print(gs_clf.cv_results_)

def gather_words(posts):
    '''
    Purpose: Split up words into one object for wordcloud and word frequency analysis 

    Inputs:
    - posts: tokenized string data

    Returns:
    - words: list of words without brackets
    '''
    words = []
    for tweet in posts:
        # Split tweet into words by comma
        # Or else iterator splits by letter, not word
        tweet_words = tweet.split(',')
        for word in tweet_words:
            # Remove brackets at end of tweet and quotes
            word = re.sub(r']', '', word)
            word = re.sub(r'\'', '', word)
            word = re.sub(r'\"', '', word)
            word = re.sub(r'\[', '', word)
            word = word.strip()
            words.append(word)

    return words

def plot_wordcloud(posts, save_image = False):
    '''
    Purpose: Given a column of words, gather them and plot a wordcloud

    Inputs: 
    posts: column of words from pandas df
    '''
    individual_words = gather_words(posts)
    wordcloud_words = ' '.join(individual_words)

    # Lower max font size
    cloud = wordcloud.WordCloud(max_font_size = 40).generate(wordcloud_words)
    plt.figure()
    plt.imshow(cloud, interpolation = 'bilinear')
    plt.axis("off")
    plt.show()

    if save_image:
        plt.savefig('images/wordcloud.png')

def scatter_plot(X, y):
    '''
    Purpose: Create scatterplot of data

    Inputs: 
    - X: attributes of data
    - y: response variable of data
    '''
    # Scatterplot
    plt.scatter(X, y)
    # Make trendline 
    trend = np.polyfit(X, y, 1)
    p = np.poly1d(trend)
    # Add to graph
    plt.plot(X, p(X), 'r--')
    plt.show()

def cross_val(clf, X_train, y_train):
    '''
    Purpose: Compute cross validation score of machine learning model

    Inputs:
    - clf: machine learning classifier object (scikit-learn)
    - X_train: training set of attributes for data
    - y_train: training set of responses for data
    '''
    scores = cross_val_score(clf, X_train, y_train, cv = 5)
    print(scores)
    print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

def success_rates(labels, predictions, return_results):
    '''
    Purpose: Display success rate of predictions for each type

    Inputs:
    - labels: names associated with predictive accuracies
    - predictions: predictive accuracy of the various labels
    - return_results: boolean to return results if true, print if false
    '''
    labels_pred = pd.DataFrame(labels, columns = ['label'])
    labels_pred['predicted'] = predictions
    labels_pred['success'] = (labels_pred['predicted'] == labels)
    fracs = {}
    for name, group in labels_pred.groupby('label'):
        frac = sum(group['success'])/len(group)
        fracs[name] = frac
    if return_results:
        return fracs
    else:
        print('Success rate for labeling personality type %s: %f' % (name, frac))

def parallelize(func, df):
    '''
    Purpose: Parallelize some of the computationally intensive functions

    Inputs: 
    - func: function we want to apply
    - df: dataframe to apply function to
    Returns:
    - end_df: dataframe from result of function
    '''
    partitions = cpu_count()
    df_subsets = np.array_split(df, partitions)
    pool = Pool(partitions)
    end_df = pd.concat(pool.map(func, df_subsets))
    pool.close()
    pool.join()

    return end_df

def find_pattern(df, text_column, pattern):
    '''
    Purpose: Extract tokens with text based on pattern given

    Inputs:
    - df: pandas dataframe we are analyzing
    - text_column: column with text to analyze (inputted as string)
    - pattern: regex pattern we want to search for (inputted as string)
    '''
    rows = df[df[text_column].str.contains(pattern)]
    #rows = df[df[text_column].str.findall(pattern)]
    print('\nRows of data with pattern %s: %s' %(pattern, rows.shape[0]))
    print(rows[text_column].head(5))

    words = gather_words(df[text_column])
    words = [word for word in words if word.startswith(pattern)]
    return words