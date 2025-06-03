from pydantic import BaseModel
from ast import literal_eval
import time

from cat.mad_hatter.decorators import tool, hook
from cat.log import log

from .todo import get_todos, save_todos, stringify_todos
from tabulate import tabulate
import csv
import os


def map_input_fields(component, field_mapping):
    """
    Map input fields to database fields.

    This function takes a component dictionary and a field mapping dictionary.
    It maps the fields from the component to the corresponding database fields
    as specified in the field mapping.

    Parameters:
    - component (dict): The component data with fields to be mapped.
    - field_mapping (dict): A dictionary mapping input field names to database field names.

    Returns:
    - dict: A dictionary with mapped fields ready for database insertion.
    """
    mapped_data = {}
    for input_field, db_field in field_mapping.items():
        if input_field in component:
            if component[input_field] is None:
                continue
            if input_field in ["unit_cost", "quantity"]:
                try:
                    mapped_data[db_field] = float(component[input_field])
                except (ValueError, TypeError):
                    mapped_data[db_field] = component[input_field]
            else:
                mapped_data[db_field] = str(component[input_field])
    return mapped_data

def validate_required_fields(mapped_data, required_fields, component_code):
    """
    Validate that all required fields are present.

    This function checks if all required fields are present in the mapped data.
    If any required fields are missing, it returns an error message.

    Parameters:
    - mapped_data (dict): The mapped component data.
    - required_fields (list): A list of required field names.
    - component_code (str): The component code for error reporting.

    Returns:
    - str or None: An error message if required fields are missing, otherwise None.
    """
    missing_fields = [field for field in required_fields if field not in mapped_data]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)} for component {component_code}. Please provide all required information."
    return None

def calculate_total_cost(unit_cost, quantity, component_code):
    """
    Calculate the total cost of a component.

    This function calculates the total cost of a component by multiplying
    the unit cost by the quantity. It handles errors related to invalid data types.

    Parameters:
    - unit_cost (float): The cost per unit of the component.
    - quantity (float): The number of units.
    - component_code (str): The component code for error reporting.

    Returns:
    - tuple: A tuple containing the total cost and an error message (if any).
    """
    try:
        total_cost = unit_cost * quantity
    except (ValueError, TypeError) as e:
        return None, f"Error calculating total cost for component {component_code}: {e}. Please ensure cost and quantity are valid numbers."
    return total_cost, None


def check_project_existence_for_user(project_name, user_id):
    """Check if a project exists for a specific user in the projects CSV file."""
    try:
        with open(project_csv_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            unique_projects = {(row[0], row[1]) for row in reader if len(row) >= 2}  # Ensure row has at least 2 columns
    except FileNotFoundError:
        return "Project file not found."

    if (project_name, str(user_id)) not in unique_projects:
        available_projects = '\n'.join(f"- {proj[0]}" for proj in unique_projects if proj[1] == str(user_id))
        return (f"Project '{project_name}' does not exist for user {user_id}. Available projects are:\n{available_projects}\n"
                "Would you like to create a new project?")
    return None


project_csv_path = os.path.join(os.path.dirname(__file__), "projects.csv")

def check_project_existence(project_name):
    """Check if a project exists in the projects CSV file."""
    try:
        with open(project_csv_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            unique_projects = {row[0] for row in reader if len(row) >= 1}  # Ensure row has at least 1 column
    except FileNotFoundError:
        return "Project file not found."

    if project_name not in unique_projects:
        available_projects = '\n'.join(f"- {proj}" for proj in unique_projects)
        return (f"Project '{project_name}' does not exist. Available projects are:\n{available_projects}\n"
                "Would you like to create a new project?")
    return None

@tool(return_direct=True)
def create_project(project_name, cat):
    """Create a new project for a specific user, tool input is the project name"""
    user_id = cat.user_id
    if not project_name or not project_name.strip():
        return "Please provide a valid project name."

    # Check if the project already exists for the user
    existence_message = check_project_existence_for_user(project_name, user_id)
    if existence_message is None:
        return f"Project '{project_name}' already exists for user {user_id}."

    # Add the new project to the CSV file
    try:
        with open(project_csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([project_name, user_id])  # Include user_id in the CSV
        return f"Project '{project_name}' has been successfully created for user {user_id}."
    except Exception as e:
        log(e, "ERROR")
        return f"Failed to create project '{project_name}' for user {user_id}: {e}"

@tool(return_direct=True)
def delete_project(project_name, cat):
    """Delete a project for a specific user, tool input is the project name"""
    user_id = cat.user_id

    # Check if the project exists for the user
    existence_message = check_project_existence_for_user(project_name, user_id)
    if existence_message:
        return existence_message

    # Remove the project from the CSV file
    try:
        with open(project_csv_path, mode='r', newline='') as file:
            projects = list(csv.reader(file))
        projects = [proj for proj in projects if not (proj[0] == project_name and proj[1] == str(user_id))]
        with open(project_csv_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(projects)
    except Exception as e:
        log(e, "ERROR")
        return f"Failed to delete project '{project_name}' for user {user_id}: {e}"

    # Delete all components associated with the project for the user
    todos = get_todos()
    todos = [todo for todo in todos if not (todo.get("nome progetto") == project_name and todo.get("user") == user_id)]
    save_todos(todos)

    return f"Project '{project_name}' and all its components have been successfully deleted for user {user_id}."

@tool(return_direct=True)
def add_component(component_data, cat):
    """Use this tool when the user ask you:
    a) To add one or more components to a project 
    b) To add following components to the bill of materials of a specific project.
    c) Aggiungere un determinato componente ad un progetto
    d) Aggiungere uno o più componenti alla distinta base di...
    
    Input should be a list of JSON objects, where each object has these fields:
    - project_name: Name of the project
    - component_code: Unique code for the component
    - description: Description of the component
    - unit_cost: Cost per unit (number)
    - quantity: Number of units (number)
    - note: (Optional) Additional notes
    
    Example for adding a single component:
    [{"project_name": "streamair", "component_code": "0200000040048", "description": "Guarnizione EE-1010", "unit_cost": 1.6, "quantity": 25, "note": "Urgent order"}]
    
    Example for adding multiple components:
    [
        {"project_name": "streamair", "component_code": "0200000040048", "description": "Guarnizione EE-1010", "unit_cost": 1.6, "quantity": 25, "note": "Urgent order"},
        {"project_name": "streamair", "component_code": "0200000040049", "description": "Valvola VT-2020", "unit_cost": 12.5, "quantity": 10}
    ]
    """

    try:
        # Replace null with None to make it compatible with literal_eval
        component_data = component_data.replace('null', 'None')
        component_data = literal_eval(component_data)
    except Exception as e:
        log(e, "ERROR")
        return f"Sorry there was an error: {e}. Can you ask in a different way?"
    
    todos = get_todos()

    # Retrieve unique project names filtered by user_id
    unique_projects = {todo["nome progetto"] for todo in todos if todo.get("user") == cat.user_id}
    unique_projects.add("None_available")

    # Check if input is a list
    if not isinstance(component_data, list):
        return "Input must be a list of component objects. Please check the format and try again."
    
    added_components = []
    
    # Define the field mapping
    field_mapping = {
        "project_name": "nome progetto",
        "component_code": "codice componente",
        "description": "Descrizione",
        "unit_cost": "Costo Unitario",
        "quantity": "Quantità",
        "note": "NOTA"
    }

    # Define the required fields
    required_fields = ["nome progetto", "codice componente", "Descrizione", "Costo Unitario", "Quantità"]

    # Determine the next ID based on the current todos
    next_id = max((todo.get("ID", 0) for todo in todos), default=0) + 1

    # Process each component in the list
    for component in component_data:
        project_name = component.get("project_name", "")
        # Use the new function to check project existence
        project_check_message = check_project_existence(project_name)
        if project_check_message:
            return project_check_message

        # Map input fields
        mapped_data = map_input_fields(component, field_mapping)

        # Validate required fields
        validation_message = validate_required_fields(mapped_data, required_fields, component.get('component_code', 'unknown'))
        if validation_message:
            return validation_message

        # Calculate total cost
        total_cost, error_message = calculate_total_cost(mapped_data["Costo Unitario"], mapped_data["Quantità"], mapped_data["codice componente"])
        if error_message:
            return error_message

        # Create component entry with ID
        component_entry = {
            "ID": next_id,  # Add the sequential ID
            "created": time.time(),
            "user": cat.user_id,
            "nome progetto": project_name,
            "codice componente": mapped_data["codice componente"],
            "Descrizione": mapped_data["Descrizione"],
            "Costo Unitario": mapped_data["Costo Unitario"],
            "Quantità": mapped_data["Quantità"],
            "Costo Totale": total_cost,
            "NOTA": mapped_data.get("NOTA", "")
        }
        
        todos.append(component_entry)
        added_components.append({
            "code": mapped_data["codice componente"],
            "project": project_name,
            "total": total_cost
        })

        # Increment the ID for the next component
        next_id += 1
    
    # Save all components at once
    save_todos(todos)

    # Generate response message
    if len(added_components) == 1:
        comp = added_components[0]
        return f"Component '{comp['code']}' added to project '{comp['project']}' with total cost {comp['total']:.2f}."
    else:
        message = f"Added {len(added_components)} components:\n"
        for comp in added_components:
            message += f"- '{comp['code']}' to project '{comp['project']}' (cost: {comp['total']:.2f})\n"
        return message

@tool(return_direct=True)
def project_summary(project_name, cat):
    """Use this tool when the user ask you about:
    a) total cost of ...
    b) the bill of material of ...
    c) la distinta base di...
    d) la distinta di ...

    Tool input is the project name as a string.
    
    """
    
    todos = get_todos()
    user_id = cat.user_id

    if not project_name or not project_name.strip():
        return "Please provide a project name."

    # Retrieve unique project names filtered by user_id
    unique_projects = {todo["nome progetto"] for todo in todos if todo.get("user") == user_id}

    # Use the new function to check project existence
    project_check_message = check_project_existence(project_name)
    if project_check_message:
        return project_check_message

    # Filter by project name and user
    project_components = [t for t in todos if t.get("nome progetto") == project_name and 
                         ('user' not in t or t['user'] == user_id)]
    
    if not project_components:
        return f"No components found for project '{project_name}'."
    
    # Calculate project totals
    total_project_cost = sum(float(comp.get("Costo Totale", 0)) for comp in project_components)
    component_count = len(project_components)
    
    # Generate summary
    summary = f"### Project Summary: {project_name}\n\n"
    summary += f"Total components: {component_count}\n"
    summary += f"Total project cost: {total_project_cost:.2f}\n\n\n"
    summary += "### Components:\n\n"

    # Prepare data for the table
    table_data = [
        [
            comp.get('ID', 'N/A'),
            comp.get('codice componente', 'N/A'),
            comp.get('Descrizione', 'N/A'),
            comp.get('Quantità', 'N/A'),
            comp.get('Costo Unitario', 'N/A'),
            comp.get('Costo Totale', 'N/A'),
            comp.get('NOTA', 'N/A')
        ]
        for comp in project_components
    ]

    # Define table headers
    headers = ["ID","Component Code", "Description", "Quantity", "Unit Cost", "Total Cost","NOTA"]

    # Generate table using tabulate
    summary += tabulate(table_data, headers=headers, tablefmt="pipe")
    return summary


@tool(return_direct=True)
def delete_components_by_ids(component_ids, cat):
    """Use this tool when the user ask you to delete some components, questions are similar to:
    a) delete all compontents with following code
    b) delete the following ids
    c) elimina tutti i ...
    
    Input should be a list of component IDs as integers.
    
    Examples: "[3]" or "[5, 10, 15]"
    """
    try:
        # Convert input string to a list of integers using literal_eval
        component_ids = literal_eval(component_ids)
        component_ids = [int(id) for id in component_ids]
    except (ValueError, SyntaxError):
        return "Invalid ID format. Please provide a string representation of a list of numeric IDs."

    todos = get_todos()
    user_id = cat.user_id

    # Track deleted components
    deleted_components = []

    # Iterate over each ID and attempt to delete
    for component_id in component_ids:
        component_to_delete = next((comp for comp in todos if comp.get("ID") == component_id and comp.get("user") == user_id), None)
        
        if component_to_delete:
            todos.remove(component_to_delete)
            deleted_components.append(component_id)

    # Save the updated list if any components were deleted
    if deleted_components:
        save_todos(todos)
        return f"Components with IDs {deleted_components} have been successfully deleted."
    else:
        return "No components found with the provided IDs."


@tool(return_direct=True)
def modify_component_by_id(modification_data, cat):
    """Use this tool when the user ask you to edit some parts of the components, questions are similar to:
    a) change the quantity of id 3 from 5 to 10
    b) change the description of id 5 to "new description"
    c) add the note "new note" to id 10
    d) aggiungi una nota "..." all’id ...

    Input should be a dictionary with the following structure:
    {
        "ID": <row_id>,
        "updates": {
            "column_name1": "new_value1",
            "column_name2": "new_value2",
            ...
        }
    }

    Example:
    {
        "ID": 3,
        "updates": {
            "Descrizione": "New Description",
            "Quantità": 50
        }
    }
    """
    try:
        modification_data = literal_eval(modification_data)
        row_id = modification_data.get("ID")
        updates = modification_data.get("updates", {})
    except Exception as e:
        log(e, "ERROR")
        return f"Invalid input format: {e}. Please provide a valid dictionary."

    # Prevent editing the ID field
    if "ID" in updates:
        return "Editing the ID field is not allowed."

    todos = get_todos()
    user_id = cat.user_id

    # Find the component to modify
    component_to_modify = next((comp for comp in todos if comp.get("ID") == row_id and comp.get("user") == user_id), None)

    if not component_to_modify:
        return f"No component found with ID {row_id}."

    # Update the component with new values
    for column, new_value in updates.items():
        if column in component_to_modify:
            component_to_modify[column] = new_value

    # Recalculate total cost if unit cost or quantity is updated
    if "Costo Unitario" in updates or "Quantità" in updates:
        unit_cost = float(component_to_modify.get("Costo Unitario", 0))
        quantity = float(component_to_modify.get("Quantità", 0))
        total_cost, error_message = calculate_total_cost(unit_cost, quantity, component_to_modify.get("codice componente"))
        if error_message:
            return error_message
        component_to_modify["Costo Totale"] = total_cost

    # Save the updated list
    save_todos(todos)
    return f"Component with ID {row_id} has been successfully updated."


@tool(return_direct=True)
def list_user_projects(tool_input,cat):
    """List all projects """
    user_id = cat.user_id
    try:
        with open(project_csv_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            user_projects = [row[0] for row in reader if len(row) >= 2 and row[1].strip() == str(user_id)]
    except FileNotFoundError:
        log("Project file not found.", "ERROR")
        return "Project file not found."
    except Exception as e:
        log(f"Error reading project file: {e}", "ERROR")
        return f"Error reading project file: {e}"

    if not user_projects:
        log(f"No projects found for user {user_id}.", "INFO")
        return f"No projects found for user {user_id}."
    
    return f"Projects for user {user_id}:\n" + '\n'.join(f"- {proj}" for proj in user_projects)

