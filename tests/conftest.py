"""Shared setup; live API requests require an explicit --live flag."""
from unittest.mock import patch

import pytest

from test_agent_notebook import load_notebook


def pytest_addoption(parser):
    parser.addoption('--live', action='store_true', help='Enable paid OpenAI integration tests')


def pytest_configure(config):
    config.addinivalue_line('markers', 'live: opt-in test making paid OpenAI requests')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--live'):
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(pytest.mark.skip(reason='requires --live (paid API requests)'))


@pytest.fixture
def agent_namespace():
    """Load definitions and local data, without reading .env or running live cells."""
    with patch('dotenv.load_dotenv', return_value=False):
        return load_notebook()


@pytest.fixture
def tool_records(agent_namespace, monkeypatch):
    """Observe actual arguments/results in memory; still execute the real tools.

    The production trace deliberately hides raw arguments. This test-only observer
    lets us check synthetic arguments without changing that privacy protection.
    """
    records = []
    for name, function in list(agent_namespace['tool_functions'].items()):
        def observe(_name=name, _function=function, **arguments):
            result = _function(**arguments)
            records.append({'tool': _name, 'arguments': arguments, 'result': result})
            return result
        monkeypatch.setitem(agent_namespace['tool_functions'], name, observe)
    return records
