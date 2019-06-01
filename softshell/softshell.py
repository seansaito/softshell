import argparse
import copy
import fileinput
import itertools
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pprint import pprint

import yaml

from softshell.exceptions import VariableNotFoundError, LoadConfigError, FileEditFailedError

REGEX_SEARCH = r'({}\s*=)[^\),]*'
REGEX_EXTRACT = r'=\s*[\"\']*(.*?)[\"\']*[\s\),;]*$'

LOGGER = logging.getLogger(__name__)


def _edit_line(line, var_name, value):
    """
    Edits the value of a variable on a given line

    Args:
        line (str): The line with the variable to change
        var_name (str): Name of the variable to change
        value (str): Value to replace the current value with
    Returns:
        (str) Edited line
    Raises:
        VariableNotFoundError
    """
    if var_name not in line:
        raise VariableNotFoundError('Variable {} could not be found in line'.format(var_name))

    # Find the portion to edit
    # This should get something like 'var_name=original_value'
    portion_to_edit = re.search(REGEX_SEARCH.format(var_name), line).group(0)

    # Extract the value after the '=' operator
    var_value = re.search(REGEX_EXTRACT, portion_to_edit).group(1)

    # replace the value
    edited_text = re.sub(var_value, value, portion_to_edit)

    # Now edit the entire line
    edited_line = re.sub(portion_to_edit, edited_text, line)

    return edited_line


def _create_back_up(path):
    """
    Creates a temporary backup file
    Args:
        path (str): Path to original file

    Returns:
        (str): Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    shutil.copy(path, temp_file.name)
    return temp_file.name


def _restore_file(temp_file, path):
    """
    Args:
        temp_file (str): Path to the temporary file 
        path (str): Path to the original file 

    Returns:
        None
    """
    shutil.copy(temp_file, path)


def _restore_from_dict(dict_files):
    """
    Restores files from dictionary

    Args:
        dict_files (dict): mapping of path => temp path

    Returns:
        None
    """
    for (path, temp) in dict_files.items():
        _restore_file(temp, path)


def _clear_from_dict(dict_files):
    """
    Clear temp files from dictionaries

    Args:
        dict_files (dict): mapping of path => temp path

    Returns:
        None
    """
    for temp in dict_files.values():
        os.remove(temp)


def edit_file(path, tuples):
    """
    Edit a file

    Args:
        path (str): Path to file
        tuples (list): List of 3-tuples of (line_number, var_name, replace_value), where
            line_number (int): Line number to look at
            var_name (str): Name of the variable
            replace_value (str): Value to insert

    Returns:
        (bool) Successful or not
    """
    # create a dictionary that maps line number to a list of (var_name, replace_value) tuples
    dict_line_number_to_pairs = {}
    for (line_number, var_name, replace_value) in tuples:
        if line_number in dict_line_number_to_pairs:
            dict_line_number_to_pairs[line_number].append((var_name, replace_value))
        else:
            dict_line_number_to_pairs[line_number] = [(var_name, replace_value)]

    # Copy the original file to a temporary location
    temp_file = _create_back_up(path)
    LOGGER.info('Temporary file of {} created at: {}'.format(path, temp_file))

    # Queue in which parsed lines are stored
    try:
        list_temporary_buffer = []
        for idx, line in enumerate(fileinput.FileInput(files=(path))):
            # Line numbers start from 1, not 0
            line_num = idx + 1
            if line_num in dict_line_number_to_pairs:
                for (var_name, replace_value) in dict_line_number_to_pairs[line_num]:
                    LOGGER.info('Configuration: {}'.format((line_num, var_name, replace_value)))
                    line = _edit_line(line, var_name, str(replace_value))
            list_temporary_buffer.append(line)

        # Save buffer
        fp = open(path, 'w+')
        fp.writelines(list_temporary_buffer)
        fp.close()
        LOGGER.info('Editing {} was successful'.format(path))
    except VariableNotFoundError as e:
        raise VariableNotFoundError('In {}: {}'.format(path, e.message))
    except:
        LOGGER.critical('Failed to edit {}; reverting to original copy'.format(path))
        _restore_file(temp_file=temp_file, path=path)
        raise FileEditFailedError('Failed to edit file {}'.format(path))

    return temp_file


def _load_config(config_path):
    """
    Load configuration file
    Args:
        config_path (str): Path to the configuration file, which must be in YAML syntax

    Returns:
        (list) Parsed configuration

    Raises:
        LoadConfigError
    """
    try:
        with open(config_path, 'r') as fp:
            configs = list(yaml.load_all(fp))
        return configs
    except Exception as e:
        raise LoadConfigError('Could not load configuration file: {}'.format(str(e)))


def _parse_config(configs):
    """
    Parse some configs
    Args:
        configs (list): List of dictionaries

    Returns:
        (list) Parsed configs
    """
    list_all_configs = []
    for dict_config in configs:
        path = dict_config['path']
        list_config_for_path = []
        for configs in dict_config['configurations']:
            line_number = configs['line_number']
            variable = configs['variable']
            value = configs['value']
            list_config_for_path.append((line_number, variable, value))
        list_all_configs.append((path, list_config_for_path))
    return list_all_configs


def _expand_configs(configs):
    """
    Create edit strategies
    Args:
        configs (list): List of dictionaries

    Returns:
        (list) Expanded configs

    Detailed description:
    Expanding a config file should look like the following:

    We start with a config file (.yml):

    (YAML)
    ```
    path: example.py
    configurations:
      - line_number: 1
        variable: LEARNING_RATE
        value: [0.1, 0.2, 0.3]
      - line_number: 2
        variable: DECAY
        value: [0.1, 0.2]
    ---
    path: example_2.py
    configurations:
      - line_number: 1
        variable: FACTOR
        value: 2
    ```

    Parsing this using PyYAML yields:

    (dictionary)
    ```
    [{'path': 'example.py',
      'configurations': [{'line_number': 1,
        'variable': 'LEARNING_RATE',
        'value': [0.1, 0.2, 0.3]},
       {'line_number': 2, 'variable': 'DECAY', 'value': [0.1, 0.2]}]},
     {'path': 'example_2.py',
      'configurations': [{'line_number': 1, 'variable': 'FACTOR', 'value': 2}]}]
    ```

    and parsing this further to enumerate all edit configurations should look like:

    (edit strategy prototype)
    ```
    [ -- edit strategy level
     [ -- edit directive level
        (example.py, [(1, LEARNING_RATE, 0.1), (2, DECAY, 0.1)]),
        (example_2.py, [(1, FACTOR, 2)]
     ],
     [
        (example.py, [(1, LEARNING_RATE, 0.1), (2, DECAY, 0.2)]),
        (example_2.py, [(1, FACTOR, 2)]
     ],
     [
        (example.py, [(1, LEARNING_RATE, 0.2), (2, DECAY, 0.1)]),
        (example_2.py, [(1, FACTOR, 2)]
     ],
     [
        (example.py, [(1, LEARNING_RATE, 0.2), (2, DECAY, 0.2)]),
        (example_2.py, [(1, FACTOR, 2)]
     ],
     [
        (example.py, [(1, LEARNING_RATE, 0.3), (2, DECAY, 0.1)]),
        (example_2.py, [(1, FACTOR, 2)]
     ],
     [
        (example.py, [(1, LEARNING_RATE, 0.3), (2, DECAY, 0.2)]),
        (example_2.py, [(1, FACTOR, 2)]
     ]
    ]

    """
    list_all_strategies = []

    dict_idx_to_file = {}
    dict_idx_to_line_number = {}
    dict_idx_to_var_name = {}

    # File name => list of edit instructions
    dict_file_to_edit_instructions = {}

    list_args_for_product = []
    running_idx = 0
    for dict_config in configs:
        path = dict_config['path']
        dict_file_to_edit_instructions[path] = []
        for config in dict_config['configurations']:
            line_number = config['line_number']
            variable = config['variable']
            dict_idx_to_file[running_idx] = path
            dict_idx_to_line_number[running_idx] = line_number
            dict_idx_to_var_name[running_idx] = variable
            values = config['value']
            if type(values) is list:
                list_args_for_product.append(values)
            else:
                list_args_for_product.append([values])
            running_idx += 1

    list_all_products = list(itertools.product(*list_args_for_product))
    for list_strategy_values in list_all_products:
        dict_file_to_edit_instructions_copy = copy.deepcopy(dict_file_to_edit_instructions)
        for value_idx, value in enumerate(list_strategy_values):
            path = dict_idx_to_file[value_idx]
            line_number = dict_idx_to_line_number[value_idx]
            var_name = dict_idx_to_var_name[value_idx]
            dict_file_to_edit_instructions_copy[path].append((line_number, var_name, value))

        list_all_strategies.append(list(dict_file_to_edit_instructions_copy.items()))

    return list_all_strategies


def main(config_path, command, verbose):
    """
    Main function

    Args:
        config_path (str): Path to configuration
        command (list): A shell command in list format

    Returns:
        None
    """
    LOGGER.info('Command is: {}'.format(command))

    if not os.path.exists(config_path):
        LOGGER.error('Check config path: {}'.format(config_path))
        raise LoadConfigError('Configuration could not be found ({})'.format(config_path))

    try:
        LOGGER.info('Loading config from {}'.format(config_path))
        configs = _load_config(config_path)
        LOGGER.info('Loading successful:')
        pprint(configs)
    except LoadConfigError as e:
        LOGGER.error(e.message)
        sys.exit(1)

    list_edit_strategies = _expand_configs(configs)

    # Start running experiments
    for idx, list_edit_strategy in enumerate(list_edit_strategies):
        LOGGER.warning('Going through edit {}/{}'.format(idx + 1, len(list_edit_strategies)))
        # Store the backup location of each file
        dict_path_to_backup = {}

        for (path, instructions) in list_edit_strategy:
            # Edit the file
            try:
                temp_file = edit_file(path, instructions)
                if verbose:
                    LOGGER.info('Edited file looks like:')
                    subprocess.run(['cat', path])

                dict_path_to_backup[path] = temp_file
                time.sleep(0.5)
            except VariableNotFoundError as e:
                LOGGER.error('Error updating file {} with the following instructions:'.format(path))
                LOGGER.error('{}'.format(instructions))
                LOGGER.error('{}'.format(e.message))
                sys.exit(1)
            except FileEditFailedError as e:
                LOGGER.error('Error updating file {} with the following instructions:'.format(path))
                LOGGER.error('{}'.format(instructions))
                LOGGER.error('{}'.format(e.message))
                sys.exit(1)

        try:
            output_file = tempfile.NamedTemporaryFile(delete=False)
            conf = 'Configuration is: {}'.format(list_edit_strategy)
            LOGGER.warning(conf)
            output_file.write('{}\n'.format(conf).encode('utf-8'))
            output_file.flush()
            LOGGER.warning('Logs can be found here: {}'.format(output_file.name))
            code = subprocess.Popen(command, stdout=output_file, stderr=output_file).wait()
            LOGGER.info('Command ended with code {}'.format(code))
            output_file.close()
        except:
            LOGGER.error('Unable to run subprocess {}'.format(command))
        finally:
            _restore_from_dict(dict_path_to_backup)
            _clear_from_dict(dict_path_to_backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='softshell', allow_abbrev=False)
    parser.add_argument('-f', required=True, type=str, help='Path to config file')
    parser.add_argument('--verbose', action='store_true', help='Set verbosity')
    parser.add_argument('command', nargs='*',
                        help='Please provide the command to run')
    args = parser.parse_args()
    args = vars(args)
    config_path = args['f']
    command = args['command']
    verbose = args['verbose']

    yaml.warnings({'YAMLLoadWarning': False})

    if verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    main(config_path=config_path, command=command, verbose=verbose)
