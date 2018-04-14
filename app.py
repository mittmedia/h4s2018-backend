import doc2topic

import re
import requests
from flask import Flask, json
app = Flask(__name__)


def find_document_type_ref(doc_text,
                           ref_types=['SOU', 'PROP', 'BET', 'MOT', 'VOT']):
    ref_tree = []
    for ref_type_index, ref_type in enumerate(ref_types):
        ref_docs = re.findall(ref_type + ' [0-9]{0,4}\:[0-9]*', doc_text)
        for ref_doc in ref_docs:
            ref_type, ref_doc = ref_doc.split(' ')
            rm, ref_doc_nr = ref_doc.split(':', 2)
            doc = find_documents({
                'doktyp': ref_type,
                'rm': rm,
                'nr': ref_doc_nr
            })
            print(doc)
            if doc and doc['dokumentlista']['dokument']:
                new_ref_types = ref_types[:ref_type_index]
                doc = doc['dokumentlista']['dokument'][0]
                ref_tree.append(doc)
                url = 'http:' + doc['dokument_url_html']
                body_html_reply = requests.get(url)
                body_text_reply = body_html_reply.text
                ref_tree += find_document_type_ref(body_text_reply,
                                                   ref_types=new_ref_types)
    return ref_tree


def document_map(doc):
    body_html_reply = requests.get('http:' + doc['dokument_url_html'])
    body_text_reply = body_html_reply.text

    topic = doc2topic.doc2topic(body_text_reply)
    return {
        'body_html': body_html_reply.text,
        'topic': topic,
        'document_type': doc['doktyp'],
        'summary': doc['summary'],
        'title': doc['titel']
    }


def documents_map(docs):
    for doc in docs:
        doc_map = document_map(doc)
        if doc_map:
            yield doc_map


def find_documents(args={}, nr_of_pages=1):
    res = {'dokumentlista': {'dokument': []}}
    for i in range(nr_of_pages):
        params = {
            'sok': '',
            'doktyp': 'prot',
            'rm': '',
            'from': '',
            'tom': '',
            'ts': '',
            'bet': '',
            'tempbet': '',
            'nr': '',
            'org': '',
            'iid': '',
            'webbtv': '',
            'talare': '',
            'exakt': '',
            'planering': '',
            'sort': 'rel',
            'sortorder': 'desc',
            'rapport': '',
            'utformat': 'json',
            'a': 's#soktraff',
            'start': i,
            **args
        }
        qs = '?' + '&'.join([str(key) + '=' + str(value)
                             for key, value in params.items()])
        doc_resp = requests.get('https://data.riksdagen.se/dokumentlista/'+qs)\
                           .json()
        res['dokumentlista']['dokument'] += \
            doc_resp['dokumentlista']['dokument']
    return res


@app.route('/documents')
def list_of_documents():
    docs = find_documents()
    return json.dumps({
        'documents': [d for ref_documents in documents_map(docs['dokumentlista']['dokument'])
                      for d in documents_map(find_document_type_ref(ref_documents['body_html']))]
    })


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
