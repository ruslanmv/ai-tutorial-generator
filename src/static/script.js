document.addEventListener('DOMContentLoaded', function() {
    const editNodeForm = document.getElementById('editNodeForm');
    if (editNodeForm) {
        editNodeForm.addEventListener('submit', function(event) {
            event.preventDefault();
            submitNodeUpdate();
        });
    }
    // Initial population or event listeners can go here if needed
});

let currentSelectedNodeId = null;

function selectNode(nodeId) {
    console.log("Selecting node:", nodeId);
    currentSelectedNodeId = nodeId;

    // Visually mark selected node in the tree
    document.querySelectorAll('#workflow-tree .tree-node').forEach(el => {
        el.classList.remove('selected');
    });
    const selectedElement = document.querySelector(`#workflow-tree .tree-node[data-id="${nodeId}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }

    fetch(`/get_node/${nodeId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
                clearEditForm();
                return;
            }
            document.getElementById('nodeId').value = data.id;
            document.getElementById('nodeTitle').value = data.title || '';
            document.getElementById('nodeBullets').value = data.bullets ? data.bullets.join('\n') : '';
        })
        .catch(error => {
            console.error('Error fetching node data:', error);
            alert('Failed to fetch node details.');
            clearEditForm();
        });
}

function clearEditForm() {
    document.getElementById('editNodeForm').reset();
    document.getElementById('nodeId').value = ''; // Clear hidden ID
    currentSelectedNodeId = null;
    document.querySelectorAll('#workflow-tree .tree-node').forEach(el => {
        el.classList.remove('selected');
    });
    console.log("Edit form cleared.");
}

function submitNodeUpdate() {
    const nodeId = document.getElementById('nodeId').value;
    const title = document.getElementById('nodeTitle').value;
    const bullets = document.getElementById('nodeBullets').value;

    if (!nodeId) {
        alert("No node selected for update. Please select a node from the list or use 'Add Node' buttons for new nodes.");
        return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('bullets', bullets);

    fetch(`/update_node/${nodeId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            reloadPageContent();
        } else {
            alert(`Error: ${data.error || 'Failed to update node.'}`);
        }
    })
    .catch(error => {
        console.error('Error updating node:', error);
        alert('An error occurred while updating the node.');
    });
}

// Updated function to handle the 'isRoot' parameter
function prepareAddNodeForm(selectedId, isChild, isRoot = false) {
    const title = prompt("Enter title for the new node:");
    if (title === null || title.trim() === "") {
        return; // User cancelled or entered empty title
    }
    addNewNode(selectedId, isChild, title, isRoot);
}

// Updated function to handle the 'isRoot' parameter
function addNewNode(selectedNodeId, asChild, title = "New Node", isRoot = false) {
    const formData = new FormData();
    formData.append('title', title);

    if (isRoot) {
        // For a root node, we ensure no parent/sibling IDs are sent.
        // The backend's add_node_route will treat it as a root node
        // if 'parent_id' and 'selected_node_id_for_sibling' are absent.
        // You could optionally add formData.append('is_root', 'true'); if your backend specifically checks for it,
        // but the current app.py logic doesn't require it.
        console.log("Adding as root node.");
    } else if (selectedNodeId) {
        if (asChild) {
            formData.append('parent_id', selectedNodeId);
            formData.append('as_child', 'true');
            console.log(`Adding as child to ${selectedNodeId}`);
        } else { // As sibling
            formData.append('selected_node_id_for_sibling', selectedNodeId);
            formData.append('as_child', 'false');
            console.log(`Adding as sibling to ${selectedNodeId}`);
        }
    } else if (!isRoot) {
        // This case (not root, but no selectedNodeId) should be prevented by UI logic.
        alert("Error: No reference node selected for adding a child or sibling.");
        return;
    }

    fetch('/add_node', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || "Node added successfully!");
            reloadPageContent(data.new_node_id); // Pass new_node_id to potentially select it after reload
        } else {
            alert(`Error: ${data.error || 'Failed to add node.'}`);
        }
    })
    .catch(error => {
        console.error('Error adding node:', error);
        alert('An error occurred while adding the node.');
    });
}

function deleteNode(nodeId) {
    if (!nodeId) {
        alert("No node selected for deletion.");
        return;
    }
    if (!confirm(`Are you sure you want to delete node ID: ${nodeId} and all its children?`)) {
        return;
    }

    fetch(`/delete_node/${nodeId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            clearEditForm(); // Clear form as the selected node is gone
            reloadPageContent();
        } else {
            alert(`Error: ${data.error || 'Failed to delete node.'}`);
        }
    })
    .catch(error => {
        console.error('Error deleting node:', error);
        alert('An error occurred while deleting the node.');
    });
}

function saveWorkflowToServer() {
    fetch('/save_workflow_file')
        .then(response => response.json())
        .then(data => alert(data.message || "Action completed."))
        .catch(error => {
            console.error('Error saving workflow:', error);
            alert('Failed to save workflow on server.');
        });
}

function loadWorkflowFromServer() {
    if (confirm("Are you sure you want to reload the workflow from the server? Any unsaved changes will be lost.")) {
        fetch('/load_workflow_file')
            .then(response => response.json())
            .then(data => {
                alert(data.message || "Action completed.");
                reloadPageContent(); // Full reload to reflect changes
            })
            .catch(error => {
                console.error('Error loading workflow:', error);
                alert('Failed to load workflow from server.');
            });
    }
}

function reloadPageContent(selectNodeIdAfterLoad = null) {
    // Reloads the entire page.
    // For a more sophisticated app, you'd update specific parts of the DOM
    // and potentially re-select the node if selectNodeIdAfterLoad is provided.
    // However, with full page reload, direct re-selection via JS is lost unless
    // the server side passes that ID back to the template to trigger selection on load.
    // The current cache-busting in index.html for the image should work with this.
    window.location.reload();
}

// Make functions globally accessible if they are called from HTML onclick attributes
window.selectNode = selectNode;
window.submitNodeUpdate = submitNodeUpdate;
window.clearEditForm = clearEditForm;
window.prepareAddNodeForm = prepareAddNodeForm;
// addNewNode is called by prepareAddNodeForm, so it doesn't strictly need to be global unless called directly from elsewhere.
// However, it doesn't hurt to keep it consistent if you might test it from console or expand.
window.addNewNode = addNewNode;
window.deleteNode = deleteNode;
window.saveWorkflowToServer = saveWorkflowToServer;
window.loadWorkflowFromServer = loadWorkflowFromServer;