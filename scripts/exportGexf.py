import json
import xml.etree.ElementTree as ET
import datetime

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def main():
    with open('registry/gaia.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    timestamp = data.get('generatedAt', datetime.datetime.now().isoformat() + 'Z')
    date_str = timestamp.split('T')[0] if 'T' in timestamp else timestamp
    skills = data.get('skills', [])
    skills.sort(key=lambda x: x['id'])
    
    # GEXF Root
    gexf = ET.Element("gexf", attrib={"xmlns": "http://www.gexf.net/1.2draft", "version": "1.2"})
    
    # Meta
    meta = ET.SubElement(gexf, "meta", attrib={"lastmodifieddate": date_str})
    creator = ET.SubElement(meta, "creator")
    creator.text = "Gaia"
    description = ET.SubElement(meta, "description")
    description.text = "Gaia Skill Registry Graph"
    
    # Graph
    graph = ET.SubElement(gexf, "graph", attrib={"defaultedgetype": "directed", "mode": "static"})
    
    # Attributes
    attributes = ET.SubElement(graph, "attributes", attrib={"class": "node"})
    ET.SubElement(attributes, "attribute", attrib={"id": "level", "title": "level", "type": "string"})
    ET.SubElement(attributes, "attribute", attrib={"id": "status", "title": "status", "type": "string"})
    ET.SubElement(attributes, "attribute", attrib={"id": "type", "title": "type", "type": "string"})
    
    nodes = ET.SubElement(graph, "nodes")
    edges = ET.SubElement(graph, "edges")
    
    edge_id = 0
    
    for skill in skills:
        node = ET.SubElement(nodes, "node", attrib={"id": skill['id'], "label": skill.get('name', skill['id'])})
        attvalues = ET.SubElement(node, "attvalues")
        ET.SubElement(attvalues, "attvalue", attrib={"for": "level", "value": skill.get('level', '')})
        ET.SubElement(attvalues, "attvalue", attrib={"for": "status", "value": skill.get('status', '')})
        ET.SubElement(attvalues, "attvalue", attrib={"for": "type", "value": skill.get('type', '')})
        
        for prereq in skill.get('prerequisites', []):
            ET.SubElement(edges, "edge", attrib={"id": f"e{edge_id}", "source": prereq, "target": skill['id']})
            edge_id += 1
            
    indent(gexf)
    tree = ET.ElementTree(gexf)
    tree.write("registry/gaia.gexf", encoding="UTF-8", xml_declaration=True)

if __name__ == '__main__':
    main()
