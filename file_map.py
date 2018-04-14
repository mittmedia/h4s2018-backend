import requests
import re

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
