#src/editor.py

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import json
import graphviz
import uuid
import os
import time # To help with cache-busting for images

app = Flask(__name__)
app.secret_key = "your_very_secret_key" # Important for session management if you use it

# --- Configuration ---
DATA_FILE = "workflow_data.json"
INITIAL_DATA_FILE = "initial_workflow.json" # Load this if DATA_FILE doesn't exist
GRAPH_OUTPUT_DIR = os.path.join('static', 'images')
GRAPH_FILENAME_BASE = "workflow_graph"

if not os.path.exists(GRAPH_OUTPUT_DIR):
    os.makedirs(GRAPH_OUTPUT_DIR)

# --- Workflow Data Management ---
workflow_data = []

def ensure_ids_and_bullets(nodes_list):
    """Recursively ensures all nodes have IDs and a 'bullets' list."""
    for node in nodes_list:
        if "id" not in node or not node["id"]:
            node["id"] = str(uuid.uuid4())
        if "bullets" not in node:
            node["bullets"] = []
        if "children" not in node:
            node["children"] = [] # Ensure children key exists
        if node["children"]: # Recurse only if children list is not empty
            ensure_ids_and_bullets(node["children"])

def load_data():
    global workflow_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
        elif os.path.exists(INITIAL_DATA_FILE): 
             with open(INITIAL_DATA_FILE, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
        else: 
            workflow_data = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Introduction",
                    "bullets": ["Start here"],
                    "children": []
                }
            ]
        ensure_ids_and_bullets(workflow_data) 
        if not os.path.exists(DATA_FILE) and not os.path.exists(INITIAL_DATA_FILE): # Save only if created from scratch
            save_data()
    except FileNotFoundError: 
        print(f"Warning: {DATA_FILE} or {INITIAL_DATA_FILE} not found. Creating default workflow.")
        workflow_data = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Introduction (Default)",
                    "bullets": ["Start by editing this workflow."],
                    "children": []
                }
            ]
        ensure_ids_and_bullets(workflow_data)
        save_data() 
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from data file: {e}. Reverting to basic structure.")
        workflow_data = [{"id": str(uuid.uuid4()), "title": "Error Loading - Corrupt JSON", "bullets": [], "children": []}]
        ensure_ids_and_bullets(workflow_data)
        save_data() 
    except Exception as e:
        print(f"Error loading data: {e}")
        workflow_data = [{"id": str(uuid.uuid4()), "title": "Error Loading - New Workflow", "bullets": [], "children": []}]
        ensure_ids_and_bullets(workflow_data)
        save_data()


def save_data():
    global workflow_data
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: 
            json.dump(workflow_data, f, indent=2, ensure_ascii=False) 
    except Exception as e:
        print(f"Error saving data: {e}")

def find_node_by_id(node_id, nodes_list=None):
    if nodes_list is None:
        nodes_list = workflow_data
    for node in nodes_list:
        if node.get("id") == node_id:
            return node
        if "children" in node and node["children"]: # Check if children list exists and is not empty
            found = find_node_by_id(node_id, node["children"])
            if found:
                return found
    return None

def get_parent_list_and_index(node_id, nodes_list=None):
    if nodes_list is None:
        nodes_list_to_search = workflow_data
    else:
        nodes_list_to_search = nodes_list

    for i, node in enumerate(nodes_list_to_search):
        if node.get("id") == node_id:
            return nodes_list_to_search, i
        if "children" in node and node["children"]: 
            found_parent_list, found_index = get_parent_list_and_index(node_id, node["children"])
            if found_index != -1: 
                return found_parent_list, found_index
    return None, -1


# --- Graphviz Rendering ---
def render_graph_image():
    """
    Renders the workflow (using global workflow_data) to an image 
    and returns its filename.
    The layout is Top-to-Bottom for parent-child relationships.
    Sibling nodes under any parent are stacked vertically using a subgraph trick.
    Top-level root nodes are also arranged sequentially from top to bottom
    using invisible edges.
    """
    # Global variables workflow_data, GRAPH_FILENAME_BASE, GRAPH_OUTPUT_DIR are used directly.

    dot = graphviz.Digraph(comment='Workflow', format='png')
    # Main direction is Top-to-Bottom for parent-child flow.
    dot.attr(rankdir='TB', splines='ortho') 
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue', fontname='Helvetica')
    dot.attr('edge', fontname='Helvetica')

    def escape_gv_html_chars(text):
        """Escapes special characters for Graphviz HTML-like labels."""
        if not isinstance(text, str):
            text = str(text) # Ensure text is a string
        return text.replace('&', '&amp;') \
                   .replace('<', '&lt;') \
                   .replace('>', '&gt;') \
                   .replace('"', '&quot;') \
                   .replace("'", '&#39;') \
                   .replace('\n', '<BR/>') # Convert newlines in data to HTML breaks

    def _add_workflow_nodes_recursively(nodes_list, parent_dot_id=None, is_processing_top_level_list=False):
        """
        Recursively adds nodes and edges to the Graphviz dot object.
        - Uses a subgraph with rank='same' for each node to stack its direct children (siblings) vertically.
        - If is_processing_top_level_list is True, adds invisible edges between the nodes in nodes_list
          to force sequential vertical layout for these top-level items.
        """
        previous_node_uid_in_current_list = None 

        for node_data in nodes_list: 
            node_uid = node_data['id']
            title = escape_gv_html_chars(node_data.get("title", "Untitled"))
            bullets_data = node_data.get("bullets", [])

            label_parts = [f"<B>{title}</B>"]

            if bullets_data:
                bullet_items_html = []
                for b_text in bullets_data:
                    escaped_bullet = escape_gv_html_chars(b_text)
                    if escaped_bullet.strip(): # Only add non-empty bullets
                        bullet_items_html.append(f"&bull; {escaped_bullet}")
                
                if bullet_items_html:
                    label_parts.append("<BR ALIGN='LEFT'/>" + "<BR ALIGN='LEFT'/>".join(bullet_items_html))

            inner_html_content = "".join(label_parts)

            full_label = f"""<
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">
                <TR><TD ALIGN="LEFT" VALIGN="MIDDLE">{inner_html_content}</TD></TR>
            </TABLE>
            >""" 

            # Subgraph trick for *every* node.
            with dot.subgraph() as s:
                s.attr(rank='same') 
                s.node(node_uid, label=full_label) 

            if parent_dot_id: 
                dot.edge(parent_dot_id, node_uid)
            elif is_processing_top_level_list and previous_node_uid_in_current_list:
                # Add invisible edge between top-level nodes for sequential vertical placement.
                dot.edge(previous_node_uid_in_current_list, node_uid, style='invis', minlen='2') 

            if "children" in node_data and node_data["children"]:
                _add_workflow_nodes_recursively(node_data["children"], node_uid, is_processing_top_level_list=False)
            
            if is_processing_top_level_list:
                previous_node_uid_in_current_list = node_uid
        
    # Initial call for the list of root workflow nodes.
    _add_workflow_nodes_recursively(workflow_data, parent_dot_id=None, is_processing_top_level_list=True)

    timestamp = int(time.time())
    output_filename_base_ts = f"{GRAPH_FILENAME_BASE}_{timestamp}" 
    graph_file_path_no_ext = os.path.join(GRAPH_OUTPUT_DIR, output_filename_base_ts)
    
    # For debugging:
    # gv_debug_filename = f"{output_filename_base_ts}.gv"
    # try:
    #     dot.save(filename=gv_debug_filename, directory=GRAPH_OUTPUT_DIR)
    #     print(f"DEBUG: Graphviz DOT source saved to: {os.path.join(GRAPH_OUTPUT_DIR, gv_debug_filename)}")
    # except Exception as e_save:
    #     print(f"DEBUG: Error saving .gv file: {e_save}")
    # print(f"DEBUG: DOT Source that would be rendered:\n{dot.source}\n")

    try:
        # Cleanup old graph files
        for old_file in os.listdir(GRAPH_OUTPUT_DIR): 
            if old_file.startswith(GRAPH_FILENAME_BASE) and \
               (old_file.endswith(".png") or old_file.endswith(".gv")):
                if not old_file.startswith(output_filename_base_ts):
                    try:
                        os.remove(os.path.join(GRAPH_OUTPUT_DIR, old_file)) 
                    except OSError as e_remove:
                        print(f"Warning: Could not remove old file {old_file}: {e_remove}")
        
        # rendered_path_with_ext = dot.render(filename=graph_file_path_no_ext, view=False, cleanup=False) # For debugging
        rendered_path_with_ext = dot.render(filename=graph_file_path_no_ext, view=False, cleanup=True)
        
        return os.path.basename(rendered_path_with_ext)
    except graphviz.backend.execute.ExecutableNotFound:
        print("CRITICAL: Graphviz 'dot' executable not found. Please install it and ensure 'dot' is in your system's PATH.")
        return None
    except Exception as e: 
        print(f"ERROR: Error rendering graph: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else str(e.stderr)
            print(f"Graphviz stderr:\n{stderr_output}")
        print(f"Problematic DOT source:\n{dot.source}")
        return None


# --- Flask Routes ---
@app.route('/')
def index():
    graph_image_file = render_graph_image()
    if graph_image_file:
        graph_image_url = url_for('static', filename=f'images/{graph_image_file}')
    else:
        graph_image_url = None 
    
    return render_template('index.html', 
                           workflow=workflow_data, 
                           graph_image_url=graph_image_url,
                           selected_node_id=None, 
                           node_data_json=json.dumps({}) 
                           )

@app.route('/get_node/<node_id>')
def get_node_data(node_id):
    node = find_node_by_id(node_id)
    if node:
        return jsonify(node)
    return jsonify({"error": "Node not found"}), 404

@app.route('/update_node/<node_id>', methods=['POST'])
def update_node_route(node_id):
    node = find_node_by_id(node_id)
    if not node:
        return jsonify({"success": False, "error": "Node not found"}), 404
    
    data = request.form
    node["title"] = data.get("title", node.get("title", "Untitled"))
    bullets_text = data.get("bullets", "")
    node["bullets"] = [b.strip() for b in bullets_text.splitlines() if b.strip()]
    
    save_data()
    return jsonify({"success": True, "message": "Node updated"})


@app.route('/add_node', methods=['POST'])
def add_node_route():
    data = request.form
    parent_id_from_payload = data.get('parent_id') 
    as_child_flag = data.get('as_child') == 'true'
    sibling_ref_id = data.get('selected_node_id_for_sibling')

    new_node_title = data.get('title', 'New Node')
    new_node_id = str(uuid.uuid4())
    new_node = {"id": new_node_id, "title": new_node_title, "bullets": [], "children": []}
    ensure_ids_and_bullets([new_node]) 

    added_to_list = None

    if parent_id_from_payload and as_child_flag:
        parent_node = find_node_by_id(parent_id_from_payload)
        if parent_node:
            if "children" not in parent_node: 
                parent_node["children"] = []
            parent_node["children"].append(new_node)
            added_to_list = parent_node["children"]
    elif sibling_ref_id and not as_child_flag: 
        parent_list_of_sibling, index_of_sibling = get_parent_list_and_index(sibling_ref_id)
        if parent_list_of_sibling is not None and index_of_sibling != -1:
            parent_list_of_sibling.insert(index_of_sibling + 1, new_node)
            added_to_list = parent_list_of_sibling
    else: 
        workflow_data.append(new_node)
        added_to_list = workflow_data
        
    if added_to_list is not None:
        save_data()
        return jsonify({"success": True, "message": "Node added successfully.", "new_node_id": new_node_id})
    else:
        return jsonify({"success": False, "error": "Could not determine where to add the node or parent/sibling reference not found."}), 400


@app.route('/delete_node/<node_id>', methods=['POST'])
def delete_node_route(node_id):
    parent_list, index = get_parent_list_and_index(node_id)
    if parent_list is not None and index != -1:
        del parent_list[index]
        save_data()
        return jsonify({"success": True, "message": "Node deleted"})
    return jsonify({"success": False, "error": "Node not found or cannot be deleted"}), 404

@app.route('/save_workflow_file', methods=['GET'])
def save_workflow_file():
    save_data()
    return jsonify({"success": True, "message": f"Workflow saved to {DATA_FILE} on server."})

@app.route('/load_workflow_file', methods=['GET']) 
def load_workflow_file():
    load_data() 
    return jsonify({"success": True, "message": "Workflow (re)loaded from server file."})

@app.route('/static/images/<filename>')
def serve_graph_image(filename):
    return send_from_directory(GRAPH_OUTPUT_DIR, filename)


# --- Initial Load ---
load_data() 

if __name__ == '__main__':
    # Check for Graphviz
    try:
        g = graphviz.Digraph(format='svg')
        g.node('a')
        g.pipe() 
        print("Graphviz 'dot' executable seems to be available.")
    except (graphviz.backend.execute.ExecutableNotFound, FileNotFoundError) as e_gv_check:
        print(f"CRITICAL: Graphviz 'dot' executable not found or failed: {e_gv_check}")
        print("Please install Graphviz and ensure 'dot' is in your system's PATH.")
        print("Visualization will likely fail.")
    except Exception as e_gv_pipe: 
        print(f"Warning: Graphviz check failed with an unexpected error: {e_gv_pipe}")
        print("This might indicate issues with Graphviz setup even if 'dot' is found.")

    app.run(debug=True)
