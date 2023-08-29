import dataclasses
import json
from typing import Optional

import aiofiles
import aiofiles.os
import networkx as nx
from dataclasses_json import DataClassJsonMixin, config
from tqdm import tqdm

from .nlp import clean_text
from .utils import load_data, dump_data


@dataclasses.dataclass(frozen=True)
class GraphData(DataClassJsonMixin):
    data_type: str = dataclasses.field(init=False, metadata=config(field_name="type"))
    uid: str

    @staticmethod
    def decode_dict(content: dict) -> 'GraphData':
        if isinstance(content, dict) and "type" in content:
            if content["type"] == "node":
                return GraphNode.from_dict(content)
            elif content["type"] == "relation":
                return GraphRelation.from_dict(content)
        raise NotImplementedError(f"Unknown value: {content}")


@dataclasses.dataclass(frozen=True)
class GraphRelation(GraphData, DataClassJsonMixin):
    data_type: str = dataclasses.field(init=False, default="relation", metadata=config(field_name="type"))
    target: str
    source: str
    weight: int


# noinspection SpellCheckingInspection
@dataclasses.dataclass(frozen=True)
class GraphNode(GraphData, DataClassJsonMixin):
    data_type: str = dataclasses.field(init=False, default="node", metadata=config(field_name="type"))
    label: str
    ntype: Optional[str] = None
    alternative_labels: Optional[list[str]] = dataclasses.field(default=None, metadata=config(field_name="alternativelabels"))


async def load_graph(file_path: str) -> nx.DiGraph:
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        graph = nx.DiGraph()
        for i in json.loads(await f.read()):
            graph_datum = GraphData.decode_dict(i)
            if isinstance(graph_datum, GraphRelation):
                graph.add_edge(graph_datum.source.lower(), graph_datum.target.lower(), data=graph_datum)
            elif isinstance(graph_datum, GraphNode):
                graph.add_node(graph_datum.uid.lower(), data=graph_datum)
            else:
                raise ValueError(f"Unknown graph data type {graph_datum}")
    return graph


def _get_category_nodes_in_graph(graph: nx.DiGraph) -> set[str]:
    def _filter_category(content: GraphNode) -> bool:
        return content.ntype in {"Category", "GATEWAY"}

    return set(filter(lambda x: _filter_category(graph.nodes[x]["data"]), graph.nodes))


def _get_all_related_nodes(graph: nx.DiGraph, node: str) -> set[str]:
    result = {node}
    for n in graph.successors(node):
        result.update(_get_all_related_nodes(graph, n))
    return result


def _get_node_labels(graph: nx.DiGraph, node: str) -> set[str]:
    node_data: GraphNode = graph.nodes[node]["data"]
    result = {node_data.label.strip()}
    if node_data.alternative_labels is not None and len(node_data.alternative_labels) > 0:
        result.update([i.strip() for i in node_data.alternative_labels if len(i) > 0])
    return result


async def get_category_labels(graph: nx.DiGraph, category_labels_path: str, model: str) -> dict[str, set[str]]:
    if await aiofiles.os.path.exists(category_labels_path):
        content: dict[str, list[str]] = await load_data(category_labels_path)
        return {k: set(v) for k, v in content.items()}
    else:
        category_labels = {
            category: {label for node in _get_all_related_nodes(graph, category) for label in _get_node_labels(graph, node) if len(label) > 0}
            for category in _get_category_nodes_in_graph(graph)
        }
        dump_dict = {}
        for k, v in tqdm(category_labels.items(), desc="Get category labels"):
            dump_dict[k] = [i for i in clean_text(v, model) if len(i) > 0]
        await dump_data(dump_dict, category_labels_path)
        return category_labels
