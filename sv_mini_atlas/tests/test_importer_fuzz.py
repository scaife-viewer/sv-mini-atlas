import hypothesis

from sv_mini_atlas.library.importers import CTSImporter, Library
from sv_mini_atlas.library.urn import URN
from sv_mini_atlas.tests.strategies import URNs


def _get_library(urn):
    textgroup_urn = urn.up_to(urn.TEXTGROUP)
    work_urn = urn.up_to(urn.WORK)
    version_urn = urn.up_to(urn.VERSION)
    library_data = {
        "text_groups": {
            textgroup_urn: {
                "urn": textgroup_urn,
                "node_kind": "textgroup",
                "name": [{"lang": "eng", "value": "Some Textgroup"}],
            }
        },
        "works": {
            work_urn: {
                "urn": work_urn,
                "groupUrn": textgroup_urn,
                "node_kind": "work",
                "lang": "grc",
                "title": [{"lang": "eng", "value": "Some Title"}],
                "versions": [
                    {
                        "urn": version_urn,
                        "node_kind": "version",
                        "version_kind": "edition",
                        "first_passage_urn": f"{version_urn}1.1-1.5",
                        "citation_scheme": None,
                        "title": [{"lang": "eng", "value": "Some Title"}],
                        "description": [{"lang": "eng", "value": "Some description."}],
                    }
                ],
            }
        },
        "versions": {
            version_urn: {
                "urn": version_urn,
                "node_kind": "version",
                "version_kind": "edition",
                "first_passage_urn": f"{version_urn}1.1-1.5",
                "citation_scheme": None,
                "title": [{"lang": "eng", "value": "Some Title"}],
                "description": [{"lang": "eng", "value": "Some description."}],
            }
        },
    }
    return Library(**library_data)


@hypothesis.given(URNs.cts_urns().map(URN))
def test_destructure(urn):
    tokens = "Some tokens"
    scheme = [f"rank_{idx + 1}" for idx, _ in enumerate(urn.passage.split("."))]
    library = _get_library(urn)
    version_data = library.versions[urn.up_to(urn.VERSION)]
    version_data.update({"citation_scheme": scheme})

    nodes = CTSImporter(library, version_data).destructure_node(urn, tokens)

    if urn.has_exemplar:
        assert len(nodes) - len(scheme) == 6
    else:
        assert len(nodes) - len(scheme) == 5

    passage_nodes = nodes[-len(scheme) :]
    for idx, node in enumerate(passage_nodes):
        # assert node["urn"] == ""
        assert node["rank"] == idx + 1
        assert node["kind"] == scheme[idx]
        if idx > 0:
            assert node["ref"].startswith(f"{passage_nodes[idx - 1]['ref']}.")
        if idx == passage_nodes.index(passage_nodes[-1]):
            assert node["text_content"] == tokens
        else:
            assert "text_content" not in node
