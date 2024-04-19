from dataclasses import dataclass

@dataclass
class Host:
    ip : str = None
    hostname : str = None
    user : str = None
    password : str = None
    os : str = None
    
