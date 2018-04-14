import doc2topic
from py2neo import Graph, Node, Relationship
import threading
import re
import requests
from flask import Flask, json, request
import time
app = Flask(__name__)
class Graph2(Graph):
    def exists(self, node):
        found_nodes = list(self.find('document', property_key='doc_id', property_value=node['doc_id']))
        return len(found_nodes) > 0


graph = Graph2(username='neo4j', password='password')

def find_document_type_ref(doc_text,
                           ref_types=['SOU', 'PROP', 'BET', 'MOT', 'VOTING']):
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
            if doc and doc['dokumentlista']['dokument']:
                new_ref_types = ref_types[:ref_type_index]
                doc = doc['dokumentlista']['dokument'][0]
                url = 'http:' + doc['dokument_url_html']
                body_html_reply = requests.get(url)
                body_text_reply = body_html_reply.text
                doc['children'] = find_document_type_ref(body_text_reply,
                                                   ref_types=new_ref_types)
                ref_tree.append(doc)
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
        if 'dokument' in doc_resp['dokumentlista']:
            res['dokumentlista']['dokument'] += \
                doc_resp['dokumentlista']['dokument']
    return res


def get_doc_id(doc):
    return doc['doktyp'] + ' ' + str(doc['rm']) + ':' + str(doc['nummer'])

def create_document_node(doc):
    return Node("document",
                doc_id=doc['doc_id'],
                title=doc['titel'],
                summary=doc['summary'],
                topic=doc2topic.doc2topic(doc),
                document_type=doc['doktyp'],
                published_at=doc['publicerad'],
                link='http:' + doc['dokument_url_html'])


created_nodes = []
def store_children_in_db(parent_node, children, tx):
    for child in children:
        child['doc_id'] = get_doc_id(child)
        child_node = create_document_node(child)
        tx = graph.begin()
        if not graph.exists(child_node) and child_node['doc_id'] not in created_nodes:
            tx.create(child_node)
            created_nodes.append(child_node['doc_id'])
        refers_relation = Relationship(parent_node, 'REFERS', child_node)
        tx.merge(refers_relation)
        tx.commit()
        if 'children' in child:
            store_children_in_db(child, child['children'], tx)


def store_in_db(docs):
    for doc in docs:
        doc['doc_id'] = get_doc_id(doc)
        document_node = create_document_node(doc)
        if not graph.exists(document_node) and document_node['doc_id'] not in created_nodes:
            tx = graph.begin()
            tx.create(document_node)
            tx.commit()
            created_nodes.append(document_node['doc_id'])
            doc_map = document_map(doc)
            children = find_document_type_ref(doc_map['body_html'])
            store_children_in_db(document_node, children, tx)


@app.route('/documents')
def list_of_documents():
    nodes = graph.run('''MATCH (fof)-[:REFERS*..5]-(d:document {doc_id:{doc_id}})
                        RETURN fof''', parameters={'doc_id': request.args['doc_id']})
    nodes = [node['fof'] for node in nodes.data()]
    return json.dumps({
        'documents': nodes
    })

@app.route('/topics')
def list_of_topics():
    return json.dumps({
        'topics': list(graph.find('document', property_key='document_type', property_value='sou'))
    })

def update_database():
    while True:
        print("Updating database...", created_nodes)
        docs = find_documents({'doktyp': 'VOTING'})['dokumentlista']['dokument'] + \
               find_documents({'doktyp': 'MOT'})['dokumentlista']['dokument'] + \
               find_documents({'doktyp': 'BET'})['dokumentlista']['dokument'] + \
               find_documents({'doktyp': 'PROP'})['dokumentlista']['dokument']
        store_in_db(docs)
        print("...update done")
        time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=update_database).start()
    app.run(debug=True, use_reloader=True, threaded=True)
