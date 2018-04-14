import gensim
import numpy
import glob
import os
import numpy as np
import sklearn.tree
from sklearn.preprocessing import normalize
import json
import file_map
import random
import requests
import pickle as pkl

sou_model = gensim.models.Doc2Vec.load(os.path.dirname(__file__) + '/sou-text.model')
labeled_doc_ids = [{"id": "BET 2017/18:8", "label": "Välfärd"}, {"id": "SOU 2017:38", "label": "Välfärd"},
                   {"id": "MOT 2017/18:1143", "label": "Välfärd"}, {"id": "SOU 2017:37", "label": "Välfärd"},
                   {"id": "SOU 2016:78", "label": "Välfärd"}, {"id": "SOU 2011:168", "label": "Försäkringar"},
                   {"id": "PROP 2017/18:3", "label": "Försäkringar"}, {"id": "SOU 2014:57", "label": "Försäkringar"},
                   {"id": "BET 2017/18:14", "label": "Försäkringar"}, {"id": "SOU 2006:99", "label": "Näringsliv"},
                   {"id": "PROP 2017/18:15", "label": "Näringsliv"}, {"id": "SOU 2016:49", "label": "Näringsliv"},
                   {"id": "BET 2017/18:5", "label": "Näringsliv"}, {"id": "SOU 2017:56", "label": "Arbetsmarknad"},
                   {"id": "MOT 2017/18:3574", "label": "Arbetsmarknad"},
                   {"id": "MOT 2017/18:3362", "label": "Arbetsmarknad"},
                   {"id": "SOU 2014:16", "label": "Arbetsmarknad"}, {"id": "SOU 2005:105", "label": "Arbetsmarknad"}]
labels = {}
for doc in labeled_doc_ids:
    if doc['label'] not in labels:
        labels[doc['label']] = len(list(labels.keys()))

random.shuffle(labeled_doc_ids)

dt_model = pkl.load(open(os.path.dirname(__file__) + '/dt.model', 'rb'))
print([labels[doc['label']] for doc in labeled_doc_ids])

def doc2topic(doc):
    doc_vec = sou_model.infer_vector(doc['titel'])
    prediction = dt_model.predict([doc_vec / np.linalg.norm(doc_vec)])[0]
    return prediction # list(labels.keys())[prediction]

def train_doc2vec():
    sou_docs = get_docs('sou-text')
    sou_model = gensim.models.Doc2Vec(sou_docs, alpha=0.025)
    sou_model.save('sou-text.model')

def train_decision_tree():
    doc_sentence = []
    doc_label = []
    for i, doc in enumerate(labeled_doc_ids):
        doktyp, doc_id = doc['id'].split(" ")
        rm, nummer = doc_id.split(':')
        doc_data = file_map.find_documents({
            'rm': rm,
            'nr': nummer,
            'doktyp': doktyp
        })
        print(doc_data)
        if doc_data and 'dokument' in doc_data['dokumentlista'] and doc_data['dokumentlista']['dokument']:
            doc['titel'] = doc_data['dokumentlista']['dokument'][0]['titel']
            body_html_reply = requests.get('http:' + doc_data['dokumentlista']['dokument'][0]['dokument_url_text'])
            body_text_reply = body_html_reply.text.split('.')
            doc_vecs = [sou_model.infer_vector(sentence.strip())
                                       for sentence in body_text_reply
                                       if len(sentence.strip()) > 0]
            doc_sentence += [doc_vec / np.linalg.norm(doc_vec) for doc_vec in doc_vecs]
            doc_label += [doc['label']] * len(doc_vecs)
        else:
            doc['titel'] = '??'

    dt_model = sklearn.tree.DecisionTreeClassifier()
    dt_model.fit(doc_sentence, doc_label)
    pkl.dump(dt_model, open('dt.model', 'wb'))


def get_docs(dir_name):
    document_count = 0
    word_list = []
    for file_name in glob.iglob(dir_name + '/*'):
        document_count = document_count + 1
        print("Processing document", document_count)
        with open(file_name, 'r', encoding='utf-8') as file_handle:
            file_content = file_handle.read()
            sentence_list = file_content.split('.')
            word_list += itereate_sentence(sentence_list)

    return word_list


def itereate_sentence(sentences):
    for i, sentence in enumerate(sentences):
        if(len(sentence.strip()) > 0):
            yield gensim.models.doc2vec.LabeledSentence(words=sentence.strip().lower().split(' '), tags=[str(i)])

if __name__ == '__main__':
    if not os.path.exists('sou-text.model'):
        print('Model does not exist')
        train_doc2vec()
    if not os.path.exists('dt.model'):
        print('Model does not exist')
        train_decision_tree()
    sou_model = gensim.models.Doc2Vec.load('sou-text.model')
    labeled_doc_ids = [{"id": "BET 2017/18:8", "label": "Välfärd"},{"id": "SOU 2017:38", "label": "Välfärd"},{"id": "MOT 2017/18:1143", "label": "Välfärd"},{"id": "SOU 2017:37", "label": "Välfärd"},{"id": "SOU 2016:78", "label": "Välfärd"},{"id": "SOU 2011:168", "label": "Försäkringar"},{"id": "PROP 2017/18:3", "label": "Försäkringar"},{"id": "SOU 2014:57", "label": "Försäkringar"},{"id": "BET 2017/18:14", "label": "Försäkringar"},{"id": "SOU 2006:99", "label": "Näringsliv"},{"id": "PROP 2017/18:15", "label": "Näringsliv"},{"id": "SOU 2016:49", "label": "Näringsliv"},{"id": "BET 2017/18:5", "label": "Näringsliv"},{"id": "SOU 2017:56", "label": "Arbetsmarknad"},{"id": "MOT 2017/18:3574", "label": "Arbetsmarknad"},{"id": "MOT 2017/18:3362", "label": "Arbetsmarknad"},{"id": "SOU 2014:16", "label": "Arbetsmarknad"},{"id": "SOU 2005:105", "label": "Arbetsmarknad"}]
    print(labeled_doc_ids)


