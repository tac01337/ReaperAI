import os
import json
import argparse

from dataclasses import dataclass
from dotenv import load_dotenv
from classes.Host import Host

"""
Load in Configuration from .env file and CLI arguments
"""
@dataclass
class Configuration:
    target : Host    
    log : str = 'memory'
    llm_connection : str = "openai_rest"
    model : str = "gpt-4-turbo-preview"
    context_size : int = 128000
    
def process_args_and_env(console) -> Configuration:
    # Load dotenv
    load_dotenv()

    # Argument parsing
    # Defaults are from .env but can be overwritten through CLI arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--target-ip', type=str, help='ssh hostname to use to connect to target system', default=os.getenv("TARGET_IP") or '127.0.0.1')

    parsed_args = arg_parser.parse_args()
    # Create main target with minimum target_ip
    target = Host(parsed_args.target_ip)

    return Configuration(target)