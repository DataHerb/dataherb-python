from dataherb.cmd.sync_git import remote_git_repo
import pytest


@pytest.mark.parametrize(
    "url, expected",
    [
        pytest.param(
            "https://github.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json",
            {
                "metadata_uri": "https://raw.githubusercontent.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json"
            },
        ),
        pytest.param(
            "https://github.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json",
            {
                "metadata_uri": "https://raw.githubusercontent.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json"
            },
        ),
        pytest.param(
            "https://github.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json",
            {
                "metadata_uri": "https://raw.githubusercontent.com/DataHerb/dataset-data-science-job/blob/main/dataherb.json"
            },
        ),
    ],
)
def test_remote_git_repo(url, expected):
    assert remote_git_repo(url)["metadata_uri"] == expected["metadata_uri"]
