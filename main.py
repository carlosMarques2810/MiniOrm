import sys
from classes.model import Table
from models import *

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Use: Python main.py migarte")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "migrate":
        Table.create_all_tables()
    else: 
        print(f"Command desconhecido: {command}")    