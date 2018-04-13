import requests
import doc2topic
import xml.etree.ElementTree as ET

from flask import Flask, json
app = Flask(__name__)

def document_map(doc):
	body_html_reply = requests.get('http:' + doc['dokument_url_html'])
	body_text_reply = body_html_reply.text

	topic = doc2topic.doc2topic(body_text_reply)
	return {
        'body_html': 'foo', #body_html_reply.text, 
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

@app.route('/documents')
def list_of_documents():
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
		'a': 's#soktraff'
	}
	qs = '?' + '&'.join([key + '=' + value for key, value in params.items()])
	doc_resp = requests.get('https://data.riksdagen.se/dokumentlista/' + qs)
	docs = doc_resp.json()

	return json.dumps({
		'documents': list(documents_map(docs['dokumentlista']['dokument']))
	})

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
