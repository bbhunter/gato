from unittest.mock import patch, MagicMock
from gato.github.search import Search
from gato.search import Searcher
from gato.cli import Output


Output(False, True)


@patch("gato.github.search.time.sleep")
@patch("gato.github.search.Api")
def test_search_api(mock_api, mock_time):

    mock_api.call_get.return_value.status_code = 200

    mock_api.call_get.return_value.json.side_effect = [{
        "items": [
            {
                "path": ".github/workflows/yaml_wf.yml",
                "repository": {
                    "fork": False,
                    "full_name": 'testOrg/testRepo'
                },
            }
        ]
    }, {
        "items": []
    }]
    mock_api.call_get.return_value.links = {}

    searcher = Search(mock_api)

    res = searcher.search_enumeration('testOrganization')
    assert len(res) == 1
    assert 'testOrg/testRepo' in res


@patch("gato.github.search.time.sleep")
@patch("gato.github.search.Api")
def test_search_api_cap(mock_api, mock_time, capfd):

    mock1 = MagicMock()
    mock1.status_code = 200

    mock1.json.return_value = {
        "items": [
            {
                "path": ".github/workflows/yaml_wf.yml",
                "repository": {
                    "fork": False,
                    "full_name": 'testOrg/testRepo'
                },
            }
        ]
    }
    mock1.links = {
            "next": {
                "url": "test"
            }
    }

    mock2 = MagicMock()
    mock2.status_code = 422

    mock_api.call_get.side_effect = [mock1, mock2]

    searcher = Search(mock_api)

    res = searcher.search_enumeration('testOrganization')
    assert len(res) == 1
    out, err = capfd.readouterr()
    assert "[-] Search failed with response code 422" in out


@patch("gato.github.search.time.sleep")
@patch("gato.github.search.Api")
def test_search_api_ratelimit(mock_api, mock_time, capfd):

    mock1 = MagicMock()
    mock1.status_code = 200

    mock1.json.return_value = {
        "items": [
            {
                "path": ".github/workflows/yaml_wf.yml",
                "repository": {
                    "fork": False,
                    "full_name": 'testOrg/testRepo'
                },
            }
        ]
    }
    mock1.links = {
            "next": {
                "url": "test"
            }
    }

    mock2 = MagicMock()
    mock2.status_code = 403

    mock3 = MagicMock()
    mock3.status_code = 200
    mock3.json.return_value = {"items": []}
    mock3.links = {}

    mock_api.call_get.side_effect = [mock1, mock2, mock3]

    searcher = Search(mock_api)

    res = searcher.search_enumeration('testOrganization')
    assert mock_time.call_count == 2
    assert len(res) == 1

    out, err = capfd.readouterr()
    assert "[!] Secondary API Rate Limit Hit." in out


@patch("gato.github.search.Api")
def test_search_api_permission(mock_api, capfd):

    mock1 = MagicMock()
    mock1.status_code = 422

    mock1.json.return_value = {
        "message": "Validation Failed",
        "errors": [
            {
                "message": "The listed users and repositories cannot be "
                "searched either because the resources do not exist or you "
                "do not have permission to view them.",
                "resource": "Search",
                "field": "q",
                "code": "invalid"
            }
        ],
        "documentation_url": "https://docs.github.com/v3/search/"
    }

    mock_api.call_get.side_effect = [mock1]

    searcher = Search(mock_api)

    res = searcher.search_enumeration('privateOrg')
    assert len(res) == 0
    out, err = capfd.readouterr()
    assert "[-] Search failed with response code 422!" in out
    assert " listed users and repositories cannot be searched " in out


@patch("gato.github.search.time.sleep")
@patch("gato.github.search.Api")
def test_search_api_iniitalrl(mock_api, mock_time, capfd):

    mock1 = MagicMock()
    mock1.status_code = 403

    mock1.json.return_value = {
        "documentation_url": "https://docs.github.com/en/free-pro-team@latest"
        "/rest/overview/resources-in-the-rest-api#secondary-rate-limits",
        "message": "You have exceeded a secondary rate limit"
        ". Please wait a few minutes before you try again."
    }

    mock2 = MagicMock()
    mock2.status_code = 200
    mock2.json.return_value = {
        "items": [
            {
                "path": ".github/workflows/yaml_wf.yml",
                "repository": {
                    "fork": False,
                    "full_name": 'testOrg/testRepo'
                },
            }
        ]
    }
    mock2.links = {}

    mock_api.call_get.side_effect = [mock1, mock2]

    searcher = Search(mock_api)

    res = searcher.search_enumeration('testOrg')
    assert len(res) == 1
    out, err = capfd.readouterr()
    assert "[!] Secondary API Rate Limit Hit." in out


@patch('gato.github.Search.search_enumeration')
@patch("gato.search.search.Api")
def test_search(mock_api, mock_search):
    mock_search.return_value = ['candidate1', 'candidate2']
    gh_search_runner = Searcher('ghp_AAAA')

    mock_api.return_value.check_user.return_value = {'user': 'user', 'scopes': [
                                                     'workflow', 'repo']}

    res = gh_search_runner.use_search_api('targetOrg')
    mock_search.assert_called_once()
    assert res is not False


@patch('gato.github.Search.search_enumeration')
@patch("gato.search.search.Api")
def test_search_query(mock_api, mock_search, capfd):
    mock_search.return_value = ['candidate1', 'candidate2']
    gh_search_runner = Searcher('ghp_AAAA')

    gh_search_runner.use_search_api(None, query="pull_request_target self-hosted")
    mock_search.assert_called_once()
    out, err = capfd.readouterr()
    assert "GitHub with the following query: pull_request_target self-hosted" in out


@patch("gato.search.search.Api.check_user")
def test_search_bad_token(mock_api):
    mock_api.return_value = False
    gh_search_runner = Searcher('ghp_AAAA')

    res = gh_search_runner.use_search_api('targetOrg')
    assert res is False


@patch('gato.search.search.requests.get')
def test_search_sourcegraph_default(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.iter_lines.return_value = [b'data: [{"repository":"test/test"}]']
    gh_search_runner = Searcher('ghp_AAAA')

    res = gh_search_runner.use_sourcegraph_api(None)

    assert 'test/test' in res


@patch('gato.search.search.requests.get')
def test_search_sourcegraph_custom(mock_get, capfd):
    mock_get.return_value.status_code = 200
    mock_get.return_value.iter_lines.return_value = [b'data: [{"repository":"test/test"}]']
    gh_search_runner = Searcher('ghp_AAAA')

    res = gh_search_runner.use_sourcegraph_api(None, 'customQuery')

    out, err = capfd.readouterr()

    assert 'customQuery' in out
    assert 'test/test' in res


@patch('gato.search.search.requests.get')
def test_search_sourcegraph_fail(mock_get, capfd):
    mock_get.return_value.status_code = 200
    mock_get.return_value.iter_lines.return_value = [b'data: {"title":"Unable To Process Query", "description":"Error"}']
    gh_search_runner = Searcher('ghp_AAAA')

    res = gh_search_runner.use_sourcegraph_api(None, ')badquery')
    out, err = capfd.readouterr()

    assert "unable to process" in out
    assert not res


@patch('gato.search.search.requests.get')
def test_search_sourcegraph_fail2(mock_get, capfd):
    mock_get.return_value.status_code = 404
    gh_search_runner = Searcher('ghp_AAAA')

    res = gh_search_runner.use_sourcegraph_api(None)
    out, err = capfd.readouterr()

    assert "returned an error" in out
    assert not res
