import json
import os
import sys
from collections import defaultdict

from django.conf import settings
from django.db.models import Max
from django.utils.translation import ugettext_noop

from treebeard.exceptions import PathOverflow

from sv_mini_atlas import constants

from .models import Node
from .urn import URN


LIBRARY_DATA_PATH = os.path.join(settings.PROJECT_ROOT, "data", "library")


class LibraryDataResolver:
    def __init__(self, data_dir_path):
        self.text_groups = {}
        self.works = {}
        self.versions = {}
        self.resolved = self.resolve_data_dir_path(data_dir_path)

    def populate_versions(self, dirpath, data):
        for version in data:
            version_part = version["urn"].rsplit(":", maxsplit=2)[1]
            version_path = os.path.join(dirpath, f"{version_part}.txt")

            if not os.path.exists(version_path):
                raise FileNotFoundError(version_path)

            self.versions[version["urn"]] = {"path": version_path, **version}

    def resolve_data_dir_path(self, data_dir_path):
        for dirpath, dirnames, filenames in sorted(os.walk(data_dir_path)):
            if "metadata.json" not in filenames:
                continue

            metadata = json.load(open(os.path.join(dirpath, "metadata.json")))
            assert metadata["node_kind"] in ["textgroup", "work"]

            if metadata["node_kind"] == "textgroup":
                self.text_groups[metadata["urn"]] = metadata
            elif metadata["node_kind"] == "work":
                self.works[metadata["urn"]] = metadata
                self.populate_versions(dirpath, metadata["versions"])

        return self.text_groups, self.works, self.versions


class Library:
    def __init__(self, text_groups, works, versions):
        self.text_groups = text_groups
        self.works = works
        self.versions = versions


class CTSImporter:
    """
    urn:cts:CTSNAMESPACE:WORK:PASSAGE
    https://cite-architecture.github.io/ctsurn_spec
    """

    CTS_URN_SCHEME = constants.CTS_URN_NODES[:-1]
    CTS_URN_SCHEME_EXEMPLAR = constants.CTS_URN_NODES
    BULK_CREATE_PASSAGE_NODES = True

    def get_version_metadata(self):
        return {
            # @@@ how much of the `metadata.json` do we
            # "pass through" via GraphQL vs
            # apply to particular node kinds in the heirarchy
            "citation_scheme": self.citation_scheme,
            "work_title": self.name,
            "first_passage_urn": self.version_data["first_passage_urn"],
            "default_toc_urn": self.version_data.get("default_toc_urn"),
        }

    def __init__(self, library, version_data, nodes=dict()):
        self.library = library
        self.version_data = version_data
        self.nodes = nodes
        self.urn = URN(self.version_data["urn"].strip())
        self.work_urn = self.urn.up_to(self.urn.WORK)
        self.name = get_first_value_for_language(
            self.library.works[self.work_urn]["title"], "eng"
        )
        self.citation_scheme = self.version_data["citation_scheme"]
        self.metadata = self.get_version_metadata()
        self.idx_lookup = defaultdict(int)

        self.nodes_to_create = []
        self.node_last_child_lookup = defaultdict()

    def add_child_to_parent_via_bulk_create(self, parent_node, child_node):
        # @@@ bastardized version of `Node._inc_path`
        # see https://github.com/django-treebeard/django-treebeard/blob/2c14a9a564cc6efc59128012aa5fc650a86a650e/treebeard/mp_tree.py#L1121

        child_node.depth = parent_node.depth + 1

        last_child = self.node_last_child_lookup.get(parent_node.urn)
        if not last_child:
            # the node had no children, adding the first child
            child_node.path = Node._get_path(parent_node.path, child_node.depth, 1)
            max_length = Node._meta.get_field("path").max_length
            if len(child_node.path) > max_length:
                raise PathOverflow(
                    ugettext_noop(
                        "The new node is too deep in the tree, try"
                        " increasing the path.max_length property"
                        " and UPDATE your database"
                    )
                )
        else:
            # adding the new child as the last one
            child_node.path = last_child._inc_path()
        self.node_last_child_lookup[parent_node.urn] = child_node
        self.nodes_to_create.append(child_node)

    def get_node_idx(self, kind):
        idx = self.idx_lookup[kind]
        self.idx_lookup[kind] += 1
        return idx

    def get_root_urn_scheme(self, node_urn):
        if node_urn.has_exemplar:
            return self.CTS_URN_SCHEME_EXEMPLAR
        return self.CTS_URN_SCHEME

    def get_urn_scheme(self, node_urn):
        return [*self.get_root_urn_scheme(node_urn), *self.citation_scheme]

    def get_partial_urn(self, kind, node_urn):
        scheme = self.get_root_urn_scheme(node_urn)
        kind_map = {kind: getattr(URN, kind.upper()) for kind in scheme}
        return node_urn.up_to(kind_map[kind])

    def destructure_node(self, node_urn, tokens):
        node_data = []
        for kind in self.get_urn_scheme(node_urn):
            data = {"kind": kind}

            if kind not in self.citation_scheme:
                data.update({"urn": self.get_partial_urn(kind, node_urn)})
                if kind == "version":
                    data.update({"metadata": self.metadata})
            else:
                ref_index = self.citation_scheme.index(kind)
                ref = ".".join(node_urn.passage_nodes[: ref_index + 1])
                urn = f"{node_urn.up_to(node_urn.NO_PASSAGE)}{ref}"
                data.update({"urn": urn, "ref": ref, "rank": ref_index + 1})
                if kind == self.citation_scheme[-1]:
                    data.update({"text_content": tokens})

            node_data.append(data)

        return node_data

    def generate_branch(self, line):
        ref, tokens = line.strip().split(maxsplit=1)
        node_urn = URN(f"{self.urn}{ref}")
        node_data = self.destructure_node(node_urn, tokens)
        for idx, data in enumerate(node_data):
            node = self.nodes.get(data["urn"])
            if node is None:
                data.update({"idx": self.get_node_idx(data["kind"])})
                if idx == 0:
                    node = Node.add_root(**data)
                elif data.get("rank") and self.BULK_CREATE_PASSAGE_NODES:
                    node = Node(**data)
                    parent = self.nodes.get(node_data[idx - 1]["urn"])
                    self.add_child_to_parent_via_bulk_create(parent, node)
                else:
                    parent = self.nodes.get(node_data[idx - 1]["urn"])
                    node = parent.add_child(**data)
                self.nodes[data["urn"]] = node

    def set_numchild(self, node):
        node.numchild = Node.objects.filter(
            path__startswith=node.path, depth=node.depth + 1
        ).count()

    def update_numchild_values(self):
        version = Node.objects.get(urn=self.version_data["urn"])

        to_update = []
        self.set_numchild(version)
        to_update.append(version)

        descendants = version.get_descendants()
        max_depth = descendants.all().aggregate(max_depth=Max("depth"))["max_depth"]
        # move this out to an expression if we can
        for node in version.get_descendants().exclude(depth=max_depth):
            self.set_numchild(node)
            to_update.append(node)
        Node.objects.bulk_update(to_update, ["numchild"], batch_size=500)

    def finalize(self):
        if self.BULK_CREATE_PASSAGE_NODES:
            Node.objects.bulk_create(self.nodes_to_create, batch_size=500)
            self.update_numchild_values()

        created_count = Node.objects.get(
            urn=self.version_data["urn"]
        ).get_descendant_count()
        return created_count

    def apply(self):
        full_content_path = self.library.versions[self.urn.absolute]["path"]
        with open(full_content_path, "r") as f:
            for line in f:
                self.generate_branch(line)

        created_count = self.finalize()
        print(f"{self.name}: {created_count + 1} nodes.", file=sys.stderr)


def resolve_library():
    text_groups, works, versions = LibraryDataResolver(LIBRARY_DATA_PATH).resolved
    return Library(text_groups, works, versions)


def get_first_value_for_language(values, lang):
    return next(iter(filter(lambda x: x["lang"] == lang, values)), None).get("value")


def import_versions():
    Node.objects.filter(kind="nid").delete()

    library = resolve_library()

    nodes = {}
    for _, version_data in library.versions.items():
        CTSImporter(library, version_data, nodes).apply()
    print(f"{Node.objects.count()} total nodes on the tree.", file=sys.stderr)
