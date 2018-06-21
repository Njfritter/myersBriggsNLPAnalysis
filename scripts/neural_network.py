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
import numpy as np
import pandas as pd
import helper_functions as hf
from data_subset import clean_df, clean_type, clean_posts
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
import pickle, os

# Neural Network parameters for tuning
parameters_nn = {
    'vect__ngram_range': [(1, 1), (1, 2)],
    'tfidf__use_idf': (True, False),
    'clf__learning_rate_init': (1e-1, 5e-1),
    'clf__hidden_layer_sizes': (50, 100),
    'clf__activation': ['identity', 'tanh', 'relu']
}

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(clean_posts, 
    clean_type, test_size = 0.33, random_state = 42)

# NEURAL NETWORK
text_clf_nn = hf.build_pipeline(CountVectorizer(),
    TfidfTransformer(),
    SelectKBest(chi2, k = 'all'),
    MLPClassifier(
        hidden_layer_sizes=(50,), 
        activation = 'identity',
        max_iter=50, 
        alpha=1e-4,
        solver='sgd', 
        verbose=10, 
        tol=1e-4, 
        random_state=1,
        learning_rate_init=.1)
)

text_clf_nn.fit(X_train, y_train)

# Evaluate performance on test set
predicted_nn = text_clf_nn.predict(X_test)
print("Training set score: %f" % text_clf_nn.score(X_train, y_train))
print("Test set score: %f" % text_clf_nn.score(X_test, y_test))
print("Number of mislabeled points out of a total %d points for the Linear SVM algorithm: %d"
    % (X_test.shape[0],(y_test != predicted_nn).sum()))

# Display success rate of predictions for each type
#rates = hf.success_rates(y_test, predicted_nn, return_results = True)
#print(rates)

# Test set calculations
test_crosstb_nb = pd.crosstab(index = y_test, columns = predicted_nn, rownames = ['class'], colnames = ['predicted'])
print(test_crosstb_nb)

# Plot success rate versus frequency
#hf.scatter_plot(list(counts), list(rates.values())) 

# Cross Validation Score
hf.cross_val(text_clf_nn, X_train, y_train)

# Do a Grid Search to test multiple parameter values
#grid_search(text_clf_nn, parameters_nn, n_jobs = 1, X_train, y_train)

# Save model (create directory for models too if it doesn't exist)
model_file = 'model/pickle_models/finalized_NN.pkl'
os.makedirs(os.path.dirname(model_file), exist_ok = True)
pickle.dump(text_clf_nn, open(model_file, 'wb'))