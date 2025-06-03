
import os
import pandas as pd


todo_csv_path = os.path.join(
    os.path.dirname(__file__), "todo.csv"
)


def stringify_todos(todos, user_id=None):
    # Filter components by user if user_id is provided
    if user_id:
        user_components = [t for t in todos if 'user' not in t or t['user'] == user_id]
    else:
        user_components = todos
        
    if len(user_components) == 0:
        return "No components found in any project."
    
    # Group components by project
    projects = {}
    for comp in user_components:
        project_name = comp.get('nome progetto', 'Unknown Project')
        if project_name not in projects:
            projects[project_name] = []
        projects[project_name].append(comp)
    
    # Build output string
    out = "### Project Components:"
    
    for project_name, components in projects.items():
        # Calculate project total
        project_total = sum(float(comp.get('Costo Totale', 0)) for comp in components)
        
        out += f"\n\n## {project_name} (Total: {project_total:.2f})"
        
        for comp in components:
            # Add user info if available and not filtering by user
            user_info = f" (by {comp['user']})" if 'user' in comp and not user_id else ""
            
            out += f"\n - {comp.get('codice componente', 'N/A')}: {comp.get('Descrizione', 'N/A')} - "
            out += f"Quantity: {comp.get('Quantità', 'N/A')}, "
            out += f"Unit cost: {comp.get('Costo Unitario', 'N/A')}, "
            out += f"Total: {comp.get('Costo Totale', 'N/A')}{user_info}"
            
            # Add note if available
            if comp.get('NOTA'):
                out += f"\n   Note: {comp.get('NOTA')}"

    return out


def get_todos():
    if not os.path.exists(todo_csv_path):
        # Create empty dataframe with the correct columns
        df = pd.DataFrame(columns=["created", "user", "nome progetto", "codice componente", 
                                  "Descrizione", "Costo Unitario", "Quantità", "Costo Totale", "NOTA"])
        df.to_csv(todo_csv_path, index=False)
        return []
    else:
        try:
            df = pd.read_csv(todo_csv_path)
            # Handle case where file exists but is empty
            if df.empty or len(df.columns) == 0:
                df = pd.DataFrame(columns=["created", "user", "nome progetto", "codice componente", 
                                          "Descrizione", "Costo Unitario", "Quantità", "Costo Totale", "NOTA"])
                df.to_csv(todo_csv_path, index=False)
            return df.to_dict(orient="records")
        except pd.errors.EmptyDataError:
            # Handle empty file error
            df = pd.DataFrame(columns=["created", "user", "nome progetto", "codice componente", 
                                      "Descrizione", "Costo Unitario", "Quantità", "Costo Totale", "NOTA"])
            df.to_csv(todo_csv_path, index=False)
            return []

    
def save_todos(todos):
    if len(todos) == 0:
        os.remove(todo_csv_path)
    else:
        pd.DataFrame(todos).to_csv(todo_csv_path, index=False)