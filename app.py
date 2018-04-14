import doc2topic
from py2neo import Graph, Node, Relationship
import threading
import re
import requests
from flask import Flask, json, request
import time
import os
import file_map

app = Flask(__name__)
class Graph2(Graph):
    def exists(self, node):
        found_nodes = list(self.find('document', property_key='doc_id', property_value=node['doc_id']))
        return len(found_nodes) > 0

username = os.getenv('NEO4J_USERNAME', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'neo4j')
graph = Graph2(username=username, password=password)


def document_map(doc):
    body_html_reply = requests.get('http:' + doc['dokument_url_html'])
    body_text_reply = body_html_reply.text

    topic = doc2topic.doc2topic(doc)
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


def get_doc_id(doc):
    return doc['doktyp'] + ' ' + str(doc['rm']) + ':' + str(doc['nummer'])

def create_document_node(doc):
    return Node("document",
                doc_id=doc['doc_id'],
                title=doc['titel'],
                summary=doc['summary'],
                topic=doc2topic.doc2topic(doc),
                document_type=doc['doktyp'],
                published_at=doc['systemdatum'],
                link='http:' + doc['dokument_url_html'])


created_nodes = []
def store_children_in_db(parent_node, children):
    for child in children:
        child['doc_id'] = get_doc_id(child)
        child_node = create_document_node(child)
        if not graph.exists(child_node) and child_node['doc_id'] not in created_nodes:
            try:
                tx = graph.begin()
                tx.create(child_node)
                created_nodes.append(child_node['doc_id'])
                tx.commit()
            except:
                print("Transaction error 2")
        try:
            tx = graph.begin()
            refers_relation = Relationship(parent_node, 'REFERS', child_node)
            tx.merge(refers_relation)
            tx.commit()
        except:
            print("Transaction error 3")
        if 'children' in child:
            store_children_in_db(child, child['children'])


def store_in_db(docs):
    for doc in docs:
        doc['doc_id'] = get_doc_id(doc)
        document_node = create_document_node(doc)
        if not graph.exists(document_node) and document_node['doc_id'] not in created_nodes:
            try:
                tx = graph.begin()
                tx.create(document_node)
                tx.commit()
                created_nodes.append(document_node['doc_id'])
            except:
                print("Transaction error 1")
            doc_map = document_map(doc)
            children = file_map.find_document_type_ref(doc_map['body_html'])
            store_children_in_db(document_node, children)

def remove_duplicates(nodes):
    list_nodes = list(nodes)
    return [node for i, node in enumerate(list_nodes) if list_nodes.index(node) == i]

@app.route('/documents')
def list_of_documents():
    nodes = graph.run('''MATCH (fof)-[:REFERS*..5]-(d:document {doc_id:{doc_id}})
                        RETURN fof''', parameters={'doc_id': request.args['doc_id']})
    nodes = [node['fof'] for node in nodes.data()
             if 'sou' not in node['fof']['doc_id'].lower()
                or request.args['doc_id'] == node['fof']['doc_id']]
    return json.dumps({
        'documents': remove_duplicates(nodes)
    })

@app.route('/topics')
def list_of_topics():
    return json.dumps({
        'topics': remove_duplicates(graph.find('document', property_key='document_type', property_value='sou'))
    })

def update_database():
    while True:
        print("Updating database...", created_nodes)
        docs = file_map.find_documents({'sok': 'Välfärd', 'doktyp': 'VOTING'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Välfärd', 'doktyp': 'MOT'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Välfärd', 'doktyp': 'BET'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Välfärd', 'doktyp': 'PROP'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Näringsliv', 'doktyp': 'VOTING'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Näringsliv', 'doktyp': 'MOT'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Näringsliv', 'doktyp': 'BET'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Näringsliv', 'doktyp': 'PROP'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Arbetsmarknad', 'doktyp': 'VOTING'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Arbetsmarknad', 'doktyp': 'MOT'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Arbetsmarknad', 'doktyp': 'BET'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Arbetsmarknad', 'doktyp': 'PROP'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Försäkring', 'doktyp': 'VOTING'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Försäkring', 'doktyp': 'MOT'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Försäkring', 'doktyp': 'BET'}, 2)['dokumentlista']['dokument'] + \
               file_map.find_documents({'sok': 'Försäkring', 'doktyp': 'PROP'}, 2)['dokumentlista']['dokument']
        store_in_db(docs)
        print("...update done")
        time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=update_database).start()
    app.run(debug=True, use_reloader=False)
