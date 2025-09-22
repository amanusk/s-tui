#!/usr/bin/env python3
"""Test script to verify the colon fix for issue #239"""

import configparser
import tempfile
import os

def test_colon_fix():
    """Test that sensor names with colons work correctly"""
    
    # Create a test config with colons
    config = configparser.ConfigParser()
    config.add_section('Temp,Summaries')
    
    # Using _COLON_ placeholder as per our fix
    config['Temp,Summaries']['sensor_COLON_0'] = 'False'
    config['Temp,Summaries']['sensor_COLON_1'] = 'True'
    config['Temp,Summaries']['normal_sensor'] = 'False'
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        config.write(f)
        temp_file = f.name
    
    print(f"Written config to {temp_file}:")
    with open(temp_file, 'r') as f:
        print(f.read())
    
    # Read it back
    config2 = configparser.ConfigParser()
    config2.read(temp_file)
    
    print("\nRead back successfully!")
    print("Sections:", config2.sections())
    print("\nItems in Temp,Summaries:")
    for key, value in config2.items('Temp,Summaries'):
        # Decode the placeholder back to colon
        decoded_key = key.replace('_colon_', ':')
        print(f'  "{decoded_key}" = "{value}"')
    
    # Clean up
    os.unlink(temp_file)
    
    # Simulate what the fixed code does
    sensor_list = ['sensor:0', 'sensor:1', 'normal_sensor']
    options_dict = dict(config2.items('Temp,Summaries'))
    
    print("\nSimulating fixed code behavior:")
    for sensor in sensor_list:
        safe_sensor = sensor.replace(':', '_COLON_').lower()  # ConfigParser lowercases keys
        if safe_sensor in options_dict:
            print(f'  Sensor "{sensor}" -> value: {options_dict[safe_sensor]}')
        else:
            print(f'  Sensor "{sensor}" -> not found, defaulting to True')

if __name__ == '__main__':
    test_colon_fix()