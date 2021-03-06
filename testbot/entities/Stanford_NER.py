import string
import nltk
import os

from nltk.corpus import stopwords as sw
from nltk.corpus import wordnet as wn
from nltk import wordpunct_tokenize
from nltk import sent_tokenize
from nltk import pos_tag
from nltk.tag import StanfordNERTagger
from nltk.chunk import ne_chunk, conlltags2tree
from nltk.tree import Tree
from .stanford_ner_client import SocketNER, load_stanford_tagger

from sklearn.base import BaseEstimator, TransformerMixin

ENTITY_TYPES = {
    'LOCATION': 'sys.location',
    'PERSON': 'sys.person',
    'ORGANIZATION': 'sys.organization',
    'MONEY': 'sys.money',
    'PERCENT': 'sys.percent',
    'DATE': 'sys.date',
    'TIME': 'sys.time'
}

class Stanford_NER_Chunker(BaseEstimator, TransformerMixin):

    def __init__(self, punct=None, tagger=None):
        load_stanford_tagger()

        self.punct = punct or set(string.punctuation)

        if (tagger == None):
            self.st_tagger = SocketNER(host='localhost',port=9199)
        else:
            self.st_tagger = tagger

    def fit(self, X, y=None):
        return self

    def inverse_transform(self, X):
        return [" ".join(doc) for doc in X]

    def transform(self, X):
        return [
            list(self.chunk(doc)) for doc in X
        ]

    def chunk(self, document):
        for sent in sent_tokenize(document):
            # tokenized_text = wordpunct_tokenize(sent)
            tagged_words = self.stanford_tagger(sent)
            bio_tagged = self.bio_tagger(tagged_words)
            sent_tree = self.stanford_tree(bio_tagged)

            for subtree in sent_tree:
                if type(subtree) == Tree:
                    ne_label = subtree.label()
                    ne_string = " ".join(
                        [token for token, pos in subtree.leaves()])
                    if ne_label in ENTITY_TYPES:
                        yield (ne_string, ENTITY_TYPES[ne_label])
                    else:
                        yield (ne_string, ne_label)

    def bio_tagger(self, ne_tagged):
        bio_tagged = []
        prev_tag = "O"
        for item in ne_tagged:
            item_split = item.split('/')
            if len(item_split) == 2:
                token = item_split[0]
                tag = item_split[1]
                if tag == "O":  # O
                    bio_tagged.append((token, tag))
                    prev_tag = tag
                    continue
                if tag != "O" and prev_tag == "O":  # Begin NE
                    bio_tagged.append((token, "B-" + tag))
                    prev_tag = tag
                elif prev_tag != "O" and prev_tag == tag:  # Inside NE
                    bio_tagged.append((token, "I-" + tag))
                    prev_tag = tag
                elif prev_tag != "O" and prev_tag != tag:  # Adjacent NE
                    bio_tagged.append((token, "B-" + tag))
                    prev_tag = tag
        return bio_tagged

    def stanford_tree(self, bio_tagged):
        tokens, ne_tags = zip(*bio_tagged)
        pos_tags = [pos for token, pos in pos_tag(tokens)]

        conlltags = [(token, pos, ne)
                     for token, pos, ne in zip(tokens, pos_tags, ne_tags)]
        ne_tree = conlltags2tree(conlltags)
        return ne_tree

    # Stanford NER tagger
    def stanford_tagger(self, token_text):
        ne_tagged = self.st_tagger.tag_text(token_text).split(' ')
        return(ne_tagged)
