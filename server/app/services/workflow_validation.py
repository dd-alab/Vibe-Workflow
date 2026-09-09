from collections import defaultdict

from app.domain.models import Workflow
from app.domain.workflow import NODE_DEFINITION_BY_TYPE

from .errors import ServiceValidationError


class WorkflowValidator:
    """Validates a local V1 workflow definition against the node registry."""

    def validate(self, workflow: Workflow) -> Workflow:
        self._validate_node_ids(workflow)
        self._validate_node_types(workflow)
        self._validate_edge_ids(workflow)
        self._validate_edges(workflow)
        self._validate_connectors(workflow)
        self._validate_acyclic(workflow)
        return workflow

    @staticmethod
    def _validate_node_ids(workflow: Workflow) -> None:
        seen: set[str] = set()
        for node in workflow.nodes:
            if node.id in seen:
                raise ServiceValidationError(
                    "Deux noeuds portent le meme identifiant."
                )
            seen.add(node.id)

    @staticmethod
    def _validate_node_types(workflow: Workflow) -> None:
        for node in workflow.nodes:
            if node.type not in NODE_DEFINITION_BY_TYPE:
                raise ServiceValidationError(
                    f"Le type de noeud '{node.type}' est inconnu."
                )

    @staticmethod
    def _validate_edge_ids(workflow: Workflow) -> None:
        seen: set[str] = set()
        for edge in workflow.edges:
            if edge.id in seen:
                raise ServiceValidationError(
                    "Deux liaisons portent le meme identifiant."
                )
            seen.add(edge.id)

    def _validate_edges(self, workflow: Workflow) -> None:
        nodes_by_id = {node.id: node for node in workflow.nodes}
        definitions = {
            node.id: NODE_DEFINITION_BY_TYPE[node.type] for node in workflow.nodes
        }
        for edge in workflow.edges:
            source_node = nodes_by_id.get(edge.source_node_id)
            target_node = nodes_by_id.get(edge.target_node_id)
            if source_node is None:
                raise ServiceValidationError(
                    f"La liaison '{edge.id}' reference un noeud source inconnu."
                )
            if target_node is None:
                raise ServiceValidationError(
                    f"La liaison '{edge.id}' reference un noeud cible inconnu."
                )
            if source_node.id == target_node.id:
                raise ServiceValidationError(
                    "Un noeud ne peut pas etre relie a lui-meme."
                )

            source_definition = definitions[source_node.id]
            target_definition = definitions[target_node.id]
            source_port = source_definition.output_ports.get(edge.source_port)
            target_port = target_definition.input_ports.get(edge.target_port)
            if source_port is None:
                raise ServiceValidationError(
                    f"Le noeud '{source_node.id}' n'a pas de port de sortie "
                    f"'{edge.source_port}'."
                )
            if target_port is None:
                raise ServiceValidationError(
                    f"Le noeud '{target_node.id}' n'a pas de port d'entree "
                    f"'{edge.target_port}'."
                )
            if source_port.type != target_port.type:
                raise ServiceValidationError(
                    f"Les ports de la liaison '{edge.id}' sont incompatibles "
                    f"({source_port.type} vers {target_port.type})."
                )

    def _validate_connectors(self, workflow: Workflow) -> None:
        for node in workflow.nodes:
            definition = NODE_DEFINITION_BY_TYPE[node.type]
            if definition.connector_required and not node.connector_id:
                raise ServiceValidationError(
                    f"Le noeud '{node.id}' requiert un connecteur."
                )
            if not definition.connector_required and node.connector_id:
                raise ServiceValidationError(
                    f"Le noeud '{node.id}' ne peut pas avoir de connecteur."
                )

    @staticmethod
    def _validate_acyclic(workflow: Workflow) -> None:
        adjacency: dict[str, set[str]] = defaultdict(set)
        in_degree: dict[str, int] = {node.id: 0 for node in workflow.nodes}
        for edge in workflow.edges:
            if edge.target_node_id not in in_degree:
                continue
            if edge.target_node_id not in adjacency[edge.source_node_id]:
                adjacency[edge.source_node_id].add(edge.target_node_id)
                in_degree[edge.target_node_id] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if visited != len(in_degree):
            raise ServiceValidationError(
                "Le workflow contient un cycle; les liaisons doivent etre acycliques."
            )
