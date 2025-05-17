import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import graphviz
import os
import platform
import uuid # For generating unique IDs

# --- Initial Workflow Data (example from user, augmented with IDs) ---
# We'll add unique IDs to each node for easier management.
# If your data doesn't have IDs, you might need to generate them
# or use paths/indices to identify nodes.

initial_workflow_data = [
    {
        "id": str(uuid.uuid4()), # Generate a unique ID
        "title": "Introduction",
        "bullets": ["What this tutorial is about"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Steps",
        "children": [
            {"id": str(uuid.uuid4()), "title": "Step 1: Setup", "bullets": []}, # Ensure bullets key exists
            {"id": str(uuid.uuid4()), "title": "Step 2: Execution", "bullets": []}
        ]
    }
]

class WorkflowEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Workflow Editor")
        self.root.geometry("1000x700")

        self.workflow_data = initial_workflow_data
        self.selected_node_id = None
        self.graphviz_path_set = self._check_graphviz_path()

        # --- Main Layout ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel: Treeview and Edit Form
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), expand=False)
        left_panel.pack_propagate(False) # Prevent resizing based on content

        # Right panel: Graph Visualization
        self.graph_panel = ttk.Frame(main_frame)
        self.graph_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.graph_label = ttk.Label(self.graph_panel, text="Workflow visualization will appear here.")
        self.graph_label.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)


        # --- Menu ---
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load Workflow", command=self.load_workflow)
        filemenu.add_command(label="Save Workflow", command=self.save_workflow)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        root.config(menu=menubar)

        # --- Treeview for Workflow Structure ---
        tree_label = ttk.Label(left_panel, text="Workflow Structure:")
        tree_label.pack(pady=(0,5), anchor='w')
        self.tree = ttk.Treeview(left_panel, selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_node_select)

        # --- Edit Form ---
        edit_frame = ttk.LabelFrame(left_panel, text="Edit Node", padding="10")
        edit_frame.pack(fill=tk.X, pady=10)

        ttk.Label(edit_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(edit_frame, textvariable=self.title_var, width=30)
        self.title_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(edit_frame, text="Bullets (one per line):").grid(row=1, column=0, sticky="nw", pady=2)
        self.bullets_text = tk.Text(edit_frame, height=5, width=30)
        self.bullets_text.grid(row=1, column=1, sticky="ew", pady=2)

        self.update_button = ttk.Button(edit_frame, text="Update Node", command=self.update_node)
        self.update_button.grid(row=2, column=0, columnspan=2, pady=5)

        # Add Node buttons
        add_node_frame = ttk.LabelFrame(left_panel, text="Add Node", padding="10")
        add_node_frame.pack(fill=tk.X, pady=10)
        self.add_sibling_button = ttk.Button(add_node_frame, text="Add Sibling", command=lambda: self.add_node(as_child=False))
        self.add_sibling_button.pack(side=tk.LEFT, expand=True, padx=2)
        self.add_child_button = ttk.Button(add_node_frame, text="Add Child", command=lambda: self.add_node(as_child=True))
        self.add_child_button.pack(side=tk.LEFT, expand=True, padx=2)
        
        self.delete_node_button = ttk.Button(add_node_frame, text="Delete Node", command=self.delete_node)
        self.delete_node_button.pack(side=tk.LEFT, expand=True, padx=2)


        # --- Initial Population ---
        self.populate_tree()
        self.render_graph()

    def _check_graphviz_path(self):
        """Checks if Graphviz is in PATH and informs user if not."""
        try:
            # Attempt to run a simple dot command
            dot = graphviz.Digraph()
            dot.pipe(format='svg') # This will raise an exception if dot is not found
            return True
        except graphviz.backend.execute.ExecutableNotFound:
            messagebox.showerror("Graphviz Not Found",
                                 "Graphviz 'dot' executable not found in your system PATH. "
                                 "Please install Graphviz and ensure it's added to your PATH. "
                                 "The visualization will not work without it.")
            return False
        except Exception as e:
            print(f"An error occurred while checking Graphviz: {e}")
            messagebox.showwarning("Graphviz Check",
                                   f"Could not verify Graphviz installation due to: {e}. "
                                   "Visualization might not work.")
            return False # Assume it might not work

    def _find_node_by_id(self, node_id, nodes_list=None):
        """Recursively find a node by its ID in the workflow data."""
        if nodes_list is None:
            nodes_list = self.workflow_data
        
        for i, node in enumerate(nodes_list):
            if node.get("id") == node_id:
                return node, nodes_list, i # Return node, its parent list, and its index
            if "children" in node:
                found_node, parent_list, index = self._find_node_by_id(node_id, node["children"])
                if found_node:
                    return found_node, parent_list, index
        return None, None, -1

    def _get_parent_list_and_index(self, node_id, nodes_list=None, parent_list_ref=None, path=None):
        """Finds the parent list and index of a node by its ID."""
        if nodes_list is None:
            nodes_list = self.workflow_data
            parent_list_ref = (self.workflow_data,) # Use a tuple to indicate top-level

        for i, node in enumerate(nodes_list):
            if node.get("id") == node_id:
                if parent_list_ref == (self.workflow_data,): # Top-level node
                    return self.workflow_data, i
                return nodes_list, i # Node found in a children list
            if "children" in node:
                found_parent_list, found_index = self._get_parent_list_and_index(node_id, node["children"], node["children"])
                if found_index != -1: # Node found in a deeper level
                    return found_parent_list, found_index
        return None, -1


    def populate_tree(self, parent_item="", nodes_list=None):
        """Populates the Treeview with workflow data."""
        if nodes_list is None:
            if parent_item == "": # Initial call
                self.tree.delete(*self.tree.get_children()) # Clear existing tree
            nodes_list = self.workflow_data

        for node in nodes_list:
            node_id = node.get("id", "N/A")
            node_title = node.get("title", "Untitled")
            # Store the actual node ID from data as the tree item ID
            tree_item_id = self.tree.insert(parent_item, "end", iid=node_id, text=node_title, open=True)
            
            if "children" in node and node["children"]:
                self.populate_tree(tree_item_id, node["children"])

    def on_node_select(self, event):
        """Handles node selection in the Treeview."""
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_node_id = None
            self.title_var.set("")
            self.bullets_text.delete("1.0", tk.END)
            return

        self.selected_node_id = selected_items[0] # This is the iid we set, which is our node's 'id'
        
        node_data, _, _ = self._find_node_by_id(self.selected_node_id)

        if node_data:
            self.title_var.set(node_data.get("title", ""))
            bullets = node_data.get("bullets", [])
            self.bullets_text.delete("1.0", tk.END)
            self.bullets_text.insert("1.0", "\n".join(bullets))
        else:
            self.title_var.set("")
            self.bullets_text.delete("1.0", tk.END)
            messagebox.showwarning("Node Not Found", f"Could not find data for node ID: {self.selected_node_id}")


    def update_node(self):
        """Updates the selected node's data and re-renders."""
        if not self.selected_node_id:
            messagebox.showwarning("No Selection", "Please select a node to update.")
            return

        node_data, _, _ = self._find_node_by_id(self.selected_node_id)
        if node_data:
            node_data["title"] = self.title_var.get()
            bullets_content = self.bullets_text.get("1.0", tk.END).strip()
            node_data["bullets"] = [b.strip() for b in bullets_content.split("\n") if b.strip()]
            
            self.populate_tree() # Repopulate tree to reflect title changes
            self.tree.selection_set(self.selected_node_id) # Re-select the node
            self.render_graph()
            messagebox.showinfo("Update", "Node updated successfully.")
        else:
            messagebox.showerror("Error", "Could not find the selected node to update.")

    def add_node(self, as_child=False):
        """Adds a new node either as a sibling or a child of the selected node."""
        if not self.selected_node_id and as_child: # Cannot add child if nothing is selected
             messagebox.showwarning("No Selection", "Please select a parent node to add a child.")
             return

        new_node_id = str(uuid.uuid4())
        new_node = {"id": new_node_id, "title": "New Node", "bullets": [], "children": []}

        if not self.selected_node_id: # Add as a top-level node
            self.workflow_data.append(new_node)
        else:
            parent_list, index_in_parent = self._get_parent_list_and_index(self.selected_node_id)
            if parent_list is None:
                messagebox.showerror("Error", "Could not find the selected node's parent.")
                return

            if as_child:
                selected_node_obj, _, _ = self._find_node_by_id(self.selected_node_id)
                if "children" not in selected_node_obj:
                    selected_node_obj["children"] = []
                selected_node_obj["children"].append(new_node)
            else: # Add as sibling
                parent_list.insert(index_in_parent + 1, new_node)
        
        self.populate_tree()
        self.tree.selection_set(new_node_id) # Select the new node
        self.on_node_select(None) # Populate edit fields for the new node
        self.render_graph()
        messagebox.showinfo("Node Added", "New node added successfully.")

    def delete_node(self):
        """Deletes the selected node."""
        if not self.selected_node_id:
            messagebox.showwarning("No Selection", "Please select a node to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected node and all its children?"):
            parent_list, index_in_parent = self._get_parent_list_and_index(self.selected_node_id)
            if parent_list is not None and index_in_parent != -1:
                del parent_list[index_in_parent]
                self.selected_node_id = None # Clear selection
                self.title_var.set("")
                self.bullets_text.delete("1.0", tk.END)
                self.populate_tree()
                self.render_graph()
                messagebox.showinfo("Node Deleted", "Node deleted successfully.")
            else:
                messagebox.showerror("Error", "Could not delete the node. It might be a top-level issue or node not found.")


    def _generate_dot_source(self, nodes_list, dot):
        """Recursively generates DOT source for Graphviz."""
        for node in nodes_list:
            node_id_str = str(node.get("id")) # Ensure ID is a string for dot
            title = node.get("title", "Untitled")
            label = title
            if node.get("bullets"):
                label += "\n\n" + "\n".join([f"- {b}" for b in node["bullets"]])
            
            dot.node(node_id_str, label=label, shape='box', style='rounded')

            if "children" in node and node["children"]:
                for child in node["children"]:
                    child_id_str = str(child.get("id"))
                    dot.edge(node_id_str, child_id_str)
                    self._generate_dot_source([child], dot) # Process child individually to connect
                # If a node has children, but they are processed recursively,
                # we still need to ensure the parent node itself is added if it wasn't part of a previous edge.
                # This is generally handled by the outer loop.
                # The recursive call here is more about establishing edges correctly.
                # A better way for children:
                # self._generate_dot_source(node["children"], dot) # Pass the children list
                # for child in node["children"]:
                #    dot.edge(node_id_str, str(child.get("id")))

    def render_graph(self):
        """Renders the workflow as a graph using Graphviz."""
        if not self.graphviz_path_set:
            self.graph_label.config(image=None, text="Graphviz is not configured. Cannot render graph.")
            return

        dot = graphviz.Digraph(comment='Workflow', format='png')
        dot.attr(rankdir='TB') # Top to Bottom layout

        # Helper to add nodes and edges recursively
        def add_to_dot(nodes, parent_dot_id=None):
            for node in nodes:
                node_uid = node['id'] # Use the unique ID
                title = node.get("title", "Untitled")
                bullets = node.get("bullets", [])
                
                label_parts = [title]
                if bullets:
                    label_parts.append("\\n" + "\\n".join([f"• {b}" for b in bullets])) # Use \\n for Graphviz newlines
                
                dot.node(node_uid, label="\\n".join(label_parts), shape='box', style='rounded,filled', fillcolor='lightblue')
                
                if parent_dot_id:
                    dot.edge(parent_dot_id, node_uid)
                
                if "children" in node and node["children"]:
                    add_to_dot(node["children"], node_uid)

        add_to_dot(self.workflow_data)

        try:
            # Save to a temporary file and load it.
            # Using a fixed name for simplicity; consider tempfile module for robustness.
            img_path = "workflow_graph" # Graphviz will append .png
            dot.render(img_path, cleanup=True) # cleanup=True removes the .gv source file
            
            # Ensure the file has the .png extension for PhotoImage
            self.graph_image = tk.PhotoImage(file=img_path + ".png")
            self.graph_label.config(image=self.graph_image, text="")
            self.graph_label.image = self.graph_image # Keep a reference
        except graphviz.backend.execute.ExecutableNotFound:
             messagebox.showerror("Graphviz Error", "Graphviz 'dot' executable not found. Please install it and add to PATH.")
             self.graph_label.config(image=None, text="Graphviz 'dot' not found.")
        except Exception as e:
            print(f"Error rendering graph: {e}")
            messagebox.showerror("Graphviz Error", f"Failed to render graph: {e}")
            self.graph_label.config(image=None, text=f"Error rendering graph: {e}")


    def load_workflow(self):
        """Loads workflow data from a JSON file."""
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath, 'r') as f:
                self.workflow_data = json.load(f)
            # Ensure IDs exist, add them if not (simple check)
            for node in self.workflow_data: # This is a shallow check, a full recursive check might be needed
                if 'id' not in node: node['id'] = str(uuid.uuid4())
                if 'children' in node:
                    for child in node['children']:
                         if 'id' not in child: child['id'] = str(uuid.uuid4())
            self.populate_tree()
            self.render_graph()
            self.selected_node_id = None # Reset selection
            self.title_var.set("")
            self.bullets_text.delete("1.0", tk.END)
            messagebox.showinfo("Load Successful", "Workflow loaded successfully.")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load workflow: {e}")

    def save_workflow(self):
        """Saves the current workflow data to a JSON file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="workflow.json"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w') as f:
                json.dump(self.workflow_data, f, indent=2)
            messagebox.showinfo("Save Successful", "Workflow saved successfully.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save workflow: {e}")


if __name__ == "__main__":
    # Check for Graphviz executable before starting Tkinter GUI
    # This is a basic check; the class has a more robust one.
    # It's good practice to ensure external dependencies are met.
    # For this example, the check within the class constructor is sufficient.

    # Note: On some systems, especially macOS with Tkinter from Python.org,
    # Graphviz might have issues finding its config if not launched from a terminal
    # that has the correct PATH.
    # If you see "format: "png" not recognized":
    # 1. Ensure Graphviz is installed (e.g., `brew install graphviz` on macOS).
    # 2. Ensure `dot` is in your PATH.
    # 3. You might need to set the `GRAPHVIZ_DOT` environment variable
    #    if Python can't find `dot` automatically.
    #    Example: os.environ["GRAPHVIZ_DOT"] = "/usr/local/bin/dot" or "/opt/homebrew/bin/dot"
    #    (Adjust the path according to your Graphviz installation)
    #    For example, on macOS with Homebrew on Apple Silicon:
    #    if platform.system() == "Darwin" and os.path.exists("/opt/homebrew/bin/dot"):
    #        os.environ["GRAPHVIZ_DOT"] = "/opt/homebrew/bin/dot"


    root = tk.Tk()
    app = WorkflowEditorApp(root)
    root.mainloop()
