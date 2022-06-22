import inspect
import os
import yaml

def load_settings():
    settings_file = 'settings.yaml'
    with open(settings_file, 'r') as file:
        return yaml.load(file, Loader=yaml.FullLoader)

settings = load_settings()
