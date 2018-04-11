# Welcome to my Myers Briggs Personality Type NLP Project
# Here I will be analyzing tweets that are labeled by their personality types
# And seeing if there is 

import matplotlib as mpl
mpl.use('TkAgg') # Need to do this everytime for some reason
import matplotlib.pyplot as plt
import random
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import csv
import re
import nltk
import wordcloud
import os
import sys
# Import libraries for model selection and feature extraction
from sklearn import (datasets, naive_bayes, feature_extraction, pipeline, linear_model,
metrics, neural_network, model_selection, feature_selection, svm)


unprocessed_data = '/Users/nathanfritter/myProjects/dataScience/myRepos/myersBriggsNLPAnalysis/data/mbti_1.csv'
processed_data = '/Users/nathanfritter/myProjects/dataScience/myRepos/myersBriggsNLPAnalysis/data/mbti_2.csv'
local_stopwords = np.empty(shape = (10, 1))
columns = np.array(['type', 'posts'])
file = pd.read_csv(unprocessed_data, names = columns)
csv_file = csv.reader(open(unprocessed_data, 'rt'))

# Parameters we will use later to tune
nb_parameters = {
  'vect__ngram_range': [(1, 1), (1, 2)],
  'tfidf__use_idf': (True, False),
  'clf__alpha': (1e-1, 1e-2, 1e-3),
  'clf__fit_prior': (True, False)
  }

svm_parameters = {
  'vect__ngram_range': [(1, 1), (1, 2)],
  'tfidf__use_idf': (True, False),
  'clf__alpha': (1e-1, 1e-2, 1e-3),
  'penalty': ['l2', 'l1', 'elasticnet'],
  'l1_ratio': (0, 0.15, 0.5, 0.75, 1),
  'learning_rate': ['constant', 'optimal', 'invscaling'],
  'eta0': (0.25, 0.5, 0.75)
}

nn_parameters = {
  'vect__ngram_range': [(1, 1), (1, 2)],
  'tfidf__use_idf': (True, False),
  #'clf__alpha': (1e-2, 1e-3),
  'learning_rate_init': (5e-2, 1e-2, 5e-3, 1e-3),
  'hidden_layer_sizes': (12, 25, 50),
  'activation': ['relu', 'identity', 'tanh', 'logistic']
}

def basic_output():
  # Basic stuff
  print(file.columns)
  print(file.shape)
  print(file.head(5))
  print(file.tail(5))

def tokenize_data():
  # Tokenize words line by line
  # Download stopwords here
  nltk.download('stopwords')
  # And write to new file so we don't have to keep doing this
  tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
  processed = csv.writer(open(processed_data, 'w+'))


  i = 0
  for line in csv_file:
    (ptype, posts) = line
    # Regular expressions
    words = re.sub(r"(?:\@|https?\://)\S+", "", posts)
    # Tokenize
    words = [word.lower() for word in tokenizer.tokenize(words)]
    words = [word for word in words if word not in nltk.corpus.stopwords.words('english') and word not in local_stopwords]

    if i % 100 == 0:
        print(i)
    i += 1

    processed.writerow([ptype] + [words])

def read_split():
  # Split up into types and posts
  processed_file = pd.read_csv(processed_data, names = columns, skiprows = [0])
  mbtitype = np.array(processed_file['type'])
  mbtiposts = np.array(processed_file['posts'])

  return mbtiposts, mbtitype

def train_test_split():
  # Split data into training and testing sets
  mbtiposts, mbtitype = read_split()

  X_train, X_test, y_train, y_test = model_selection.train_test_split(
  mbtiposts, mbtitype, test_size=0.33, random_state=42)

  return X_train, X_test, y_train, y_test

def build_pipeline(model):
  # Build pipelines for models
  text_clf = pipeline.Pipeline([
   ('vect', feature_extraction.text.CountVectorizer()),
   ('tfidf', feature_extraction.text.TfidfTransformer()),
   ('chi2', feature_selection.SelectKBest(feature_selection.chi2, k = 'all')),
   ('clf', model),
  ])

  return text_clf

def grid_search(clf, parameters, jobs, X, y):  
  # Perform grid search
  gs_clf = model_selection.GridSearchCV(clf, 
    param_grid = parameters, 
    n_jobs = jobs,
    verbose = 7
    )
  gs_clf = gs_clf.fit(X, y)

  best_parameters, score, _ = max(gs_clf.grid_scores_, key = lambda x: x[1])
  for param_name in sorted(parameters.keys()):
    print("%s: %r" % (param_name, best_parameters[param_name]))
  print(score)

def gather_words(posts):
  
  words = []
  for tweet in posts:
    # Split tweet into words by comma
    # Or else iterator splits by letter, not word
    tweet_words = tweet.split(',')
    for word in tweet_words:
      # Remove brackets at end of tweet and quotes
      word = re.sub(r"]", "", word)
      word = re.sub(r"\'", "", word)
      words.append(word)

  return words

def unique_labels_word_freq():

  mbtiposts, mbtitype = read_split()

  # Show counts of personality types of tweets
  unique, counts = np.unique(mbtitype, return_counts=True)
  print(np.asarray((unique, counts)).T)

  # Gather list of words
  words = gather_words(mbtiposts)

  words_top_25 = []
  freq_top_25 = []
  word_features = nltk.FreqDist(words)
  print("\nMost frequent words with counts:")
  for word, frequency in word_features.most_common(25):
    print('%s: %d' % (word, frequency))
    words_top_25.append(word.title())
    freq_top_25.append(frequency)

  # Now to make bar graphs
  # First for the type frequencies
  fig, ax = plt.subplots()
  width = 0.5
  ind = np.arange(len(unique))
  ax.barh(ind, counts, width, color = 'red')
  ax.set_yticks(ind + width / 2)
  ax.set_yticklabels(unique, minor = False)
  for i, v in enumerate(counts):
    ax.text(v + 2, i - 0.125, str(v), color = 'blue', fontweight = 'bold')
  plt.title('Personality Type Frequencies')
  plt.xlabel('Frequency')
  plt.ylabel('Type')
  plt.show()

  # Now top 25 word frequencies
  fig, ax = plt.subplots()
  width = 0.5
  unique, counts = np.array(words_top_25), np.array(freq_top_25)
  ind = np.arange(len(unique))
  ax.barh(ind, counts, width, color = 'red')
  ax.set_yticks(ind + width / 2)
  ax.set_yticklabels(unique, minor = False)
  for i, v in enumerate(counts):
    ax.text(v + 2, i - 0.25, str(v), color = 'blue', fontweight = 'bold')
  plt.title('Top 25 Word Frequencies')
  plt.xlabel('Frequency')
  plt.ylabel('Word')
  plt.show()



def word_cloud():

  mbtiposts, mbtitype = read_split()

  # Gather list of words
  words = gather_words(mbtiposts)

  wordcloud_words = " ".join(words)
  # Lower max font size
  cloud = wordcloud.WordCloud(max_font_size = 40).generate(wordcloud_words)
  plt.figure()
  plt.imshow(cloud, interpolation = 'bilinear')
  plt.axis("off")
  plt.show()

def cross_val(clf, X_train, y_train):
  # Cross Validation Score
  scores = model_selection.cross_val_score(clf, X_train, y_train, cv = 5)
  print(scores)
  print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

def initial_model():
  # Split data into training and testing sets
  X_train, X_test, y_train, y_test = train_test_split()

  # Extract features from text files
  count_vect = feature_extraction.text.CountVectorizer(tokenizer=lambda doc: doc, lowercase=False)
  X_train_counts = count_vect.fit_transform(X_train)
  print(X_train_counts.shape)

  tfidf_transformer = feature_extraction.text.TfidfTransformer()
  X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
  print(X_train_tfidf.shape)

  # Training a classifer
  clf = naive_bayes.MultinomialNB()
  clf = clf.fit(X_train_tfidf, y_train)
  INTJ_sentence = ['Writing college essays is stressful because I have to give a stranger a piece of myself and that piece has to incorporate all of who I am']
  INTJ_X_new_counts = count_vect.transform(INTJ_sentence)
  INTJ_X_new_tfidf = tfidf_transformer.transform(INTJ_X_new_counts)

  ENFP_sentence = ['Our favorite friendships are the ones where you can go from talking about the latest episode of the Bachelorette to the meaning of life']
  ENFP_X_new_counts = count_vect.transform(ENFP_sentence)
  ENFP_X_new_tfidf = tfidf_transformer.transform(ENFP_X_new_counts)
  # Make a prediction of test sentence
  predictedINTJ = clf.predict(INTJ_X_new_tfidf)
  predictedENFP = clf.predict(ENFP_X_new_tfidf)
  for words, category in zip(INTJ_sentence, predictedINTJ):
    print('%r => %s' % (INTJ_sentence, category))
  for words, category in zip(ENFP_sentence, predictedENFP):
    print('%r => %s' % (ENFP_sentence, category))

def naive_bayes_model():
  # Split data into training and testing sets
  X_train, X_test, y_train, y_test = train_test_split()

  # Naive Bayes model fitting and predictions
  # Building a Pipeline; this does all of the work in intial_model()  
  text_clf = build_pipeline(naive_bayes.MultinomialNB())
  text_clf = text_clf.fit(X_train, y_train)

  # Evaluate performance on test set
  predicted = text_clf.predict(X_test)
  print("The accuracy of the Naive Bayes algorithm is: ") 
  print(np.mean(predicted == y_test))
  print("The test error rate of the Naive Bayes algorithm is: ")
  print(1 - np.mean(predicted == y_test))
  print("Number of mislabeled points out of a total %d points for the Naive Bayes algorithm : %d"
    % (X_test.shape[0],(y_test != predicted).sum()))

  # Cross Validation
  mbtiposts, mbtitype = read_split()
  cross_val(text_clf, mbtiposts, mbtitype)

  # Do a Grid Search to test multiple parameter values
  grid_search(text_clf, nb_parameters, 1, X_train, y_train)

def linear_SVM_model():
  # Split data into training and testing sets
  X_train, X_test, y_train, y_test = train_test_split()

  # Linear Support Vector Machine w/ stochastic gradient descent (SGD) learning
  # This model can be other linear models, but using "hinge" makes it a SVM
  # Build Pipeline again

  text_clf_two = build_pipeline(linear_model.SGDClassifier(
   loss='hinge',
   penalty='l2',
   alpha=1e-3,
   max_iter=5,
   learning_rate = 'optimal',
   random_state=42))

  text_clf_two = text_clf_two.fit(X_train, y_train)
  predicted_two = text_clf_two.predict(X_test)
  print("The accuracy of the Linear SVM is: ")
  print(np.mean(predicted_two == y_test))
  print("The test error rate of the Linear SVM algorithm is: ")
  print(1 - np.mean(predicted_two == y_test))
  print("Number of mislabeled points out of a total %d points for the Linear SVM algorithm: %d"
    % (X_test.shape[0],(y_test != predicted_two).sum()))

  # Cross Validation
  mbtiposts, mbtitype = read_split()
  cross_val(text_clf_two, mbtiposts, mbtitype)

  # Do a Grid Search to test multiple parameter values
  #grid_search(text_clf_two, svm_parameters, -1, X_train, y_train)


def neural_network_model():
  # Split data into training and testing sets
  X_train, X_test, y_train, y_test = train_test_split()

  # NEURAL NETWORK
  text_clf_three = build_pipeline(neural_network.MLPClassifier(
    hidden_layer_sizes=(50,), 
    max_iter=50, 
    alpha=1e-4,
    solver='sgd', 
    verbose=10, 
    tol=1e-4, 
    random_state=1,
    learning_rate_init=.1))

  text_clf_three.fit(X_train, y_train)
  print("Training set score: %f" % text_clf_three.score(X_train, y_train))
  print("Test set score: %f" % text_clf_three.score(X_test, y_test))

  # Cross Validation Score
  mbtiposts, mbtitype = read_split()
  cross_val(text_clf_three, mbtiposts, mbtitype)

  # Do a Grid Search to test multiple parameter values
  #grid_search(text_clf_three, nn_parameters, -1, X_train, y_train)


if __name__ == '__main__':
  if len(sys.argv) == 2:
    if sys.argv[1] == 'basic':
      basic_output()
    elif sys.argv[1] == 'tokenize':
      tokenize_data()
    elif sys.argv[1] == 'unique':
      unique_labels_word_freq()
    elif sys.argv[1] == 'cloud':
      word_cloud()
    elif sys.argv[1] == 'initial':
      initial_model()
    elif sys.argv[1] == 'NB':
      naive_bayes_model()
    elif sys.argv[1] == 'SVM':
      linear_SVM_model()
    elif sys.argv[1] == 'NN':
      neural_network_model()
    else:
      print("Incorrect keyword; please try again.")
  else:
    print("Incorrect number of keywords; please enter only one keyword.")