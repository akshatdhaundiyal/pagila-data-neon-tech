import re

def clean_sql(sql_content, target_user="neondb_owner"):
    """
    Cleans SQL content and separates FK constraints.
    Returns (cleaned_base_sql, constraints_sql).
    """
    # Replace ownership
    sql_content = sql_content.replace("OWNER TO postgres", f"OWNER TO {target_user}")
    
    lines = sql_content.splitlines()
    base_lines = []
    constraint_lines = []
    
    is_constraint_section = False
    
    for line in lines:
        # Check if we are entering the FK constraints section
        if "Type: FK CONSTRAINT" in line:
            is_constraint_section = True
            
        # Detect psql meta-commands
        if line.strip().startswith("\\"):
            continue
            
        # Fix generated columns missing 'STORED'
        if "GENERATED ALWAYS AS" in line and "STORED" not in line:
            if line.strip().endswith(","):
                line = re.sub(r"(\)\s*),$", r") STORED,", line)
            elif line.strip().endswith(");"):
                line = re.sub(r"(\)\s*)\);$", r") STORED);", line)
            elif line.rstrip().endswith(")"):
                line = re.sub(r"(\)\s*)$", r") STORED", line)
        
        # Remove trigger disable/enable commands
        if "DISABLE TRIGGER ALL" in line or "ENABLE TRIGGER ALL" in line:
            continue

        if is_constraint_section:
            constraint_lines.append(line)
        else:
            base_lines.append(line)
            
    return "\n".join(base_lines), "\n".join(constraint_lines)
