import configparser
import os
import re
import semver
from invoke import run


def get_current_version():
    return run('python setup.py --version', hide=True).stdout.strip()


def evaluate_version_bump(force=None):
    if force:
        return force
    return 'patch'


def get_new_version(current_version, level_bump):
    return getattr(semver, 'bump_{0}'.format(level_bump))(current_version)


def set_new_version(new_version):
    filename, variable = load_config().get('version_variable').split(':')
    variable = variable.strip()
    with open(filename, mode='r') as fr:
        content = fr.read()

    content = re.sub(
        r'{} ?= ?["\']\d+\.\d+(?:\.\d+)?["\']'.format(variable),
        '{} = \'{}\''.format(variable, new_version),
        content
    )

    with open(filename, mode='w') as fw:
        fw.write(content)
    return True


def load_config():
    config = configparser.ConfigParser()
    with open(os.path.join(os.getcwd(), 'setup.cfg')) as f:
        config.read_file(f)
    return config._sections['semantic_release']