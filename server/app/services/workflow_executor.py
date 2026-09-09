import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.domain.models import (
    Asset,
    AssetKind,
    Character,
    RunStatus,
    Workflow,
    WorkflowNode,
    WorkflowRun,
)
from app.repositories.asset_repository import AssetRepository
from app.repositories.workflow_repository import WorkflowRepository

from .job_runner import JobRunner
from .thumbnail_service import ThumbnailService


@dataclass
class NodeContext:
    project_directory: Path
    workflow: Workflow
    run: WorkflowRun
    node: WorkflowNode
    character: Character | None
    current_character: Character | None
    job_ids: list[UUID] = field(default_factory=list)


class WorkflowExecutor:
    def __init__(
        self,
        jobs: JobRunner,
        assets: AssetRepository,
        workflows: WorkflowRepository,
        thumbnails: ThumbnailService | None = None,
    ) -> None:
        self.jobs = jobs
        self.assets = assets
        self.workflows = workflows
        self.thumbnails = thumbnails or ThumbnailService(
            max_width=16_384,
            max_height=16_384,
            max_pixels=100_000_000,
            thumbnail_max_dimension=512,
        )

    def execute(
        self,
        project_id: UUID,
        workflow_id: UUID,
        run: WorkflowRun,
    ) -> WorkflowRun:
        workflow = self.workflows.get(project_id, workflow_id)
        project_directory = self.assets.projects.path_for(project_id)
        character = (
            self.assets.get_character(project_id, run.character_id)
            if run.character_id is not None
            else None
        )
        order = self._topological_order(workflow)
        node_outputs: dict[str, dict[str, Any]] = {}
        ctx = NodeContext(
            project_directory=project_directory,
            workflow=workflow,
            run=run,
            node=workflow.nodes[0],
            character=character,
            current_character=character,
        )
        try:
            for node in order:
                ctx.node = node
                inputs = self._resolve_inputs(workflow, node, node_outputs)
                outputs = self._execute_node(project_id, ctx, inputs)
                node_outputs[node.id] = outputs
            return run.model_copy(
                update={"status": RunStatus.COMPLETED, "job_ids": list(ctx.job_ids)}
            )
        except Exception:
            return run.model_copy(
                update={"status": RunStatus.FAILED, "job_ids": list(ctx.job_ids)}
            )

    def _execute_node(
        self,
        project_id: UUID,
        ctx: NodeContext,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        node_type = ctx.node.type
        if node_type == "character_input":
            return {"character": str(ctx.character.id) if ctx.character else None}
        if node_type == "prompt_variant":
            return {"prompt": ctx.node.parameters.get("prompt_text", "")}
        if node_type == "image_generation":
            return self._run_generation(project_id, ctx, inputs)
        if node_type == "result_set":
            return self._publish(project_id, ctx, inputs, AssetKind.GENERATION)
        if node_type == "selection":
            return self._run_selection(ctx)
        if node_type == "upscale":
            return self._publish(
                project_id, ctx, inputs, AssetKind.UPSCALE, run_connector=True
            )
        if node_type == "export":
            return self._publish(project_id, ctx, inputs, AssetKind.EXPORT)
        return {}

    def _run_generation(
        self, project_id: UUID, ctx: NodeContext, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        if ctx.current_character is None:
            raise ValueError("generation requires a character context")
        job = self.jobs.create_job(
            project_id,
            workflow_id=ctx.workflow.id,
            run_id=ctx.run.id,
            node_id=ctx.node.id,
            character_id=ctx.current_character.id,
            connector_id=ctx.node.connector_id,
            parameters=ctx.node.parameters,
            inputs=inputs,
        )
        ctx.job_ids.append(job.id)
        result = self.jobs.run_job(project_id, job)
        return {"image": str(result.output_path)}

    def _publish(
        self,
        project_id: UUID,
        ctx: NodeContext,
        inputs: dict[str, Any],
        kind: AssetKind,
        *,
        run_connector: bool = False,
    ) -> dict[str, Any]:
        if ctx.current_character is None:
            raise ValueError("publishing an asset requires a character context")
        character = ctx.current_character
        with self.assets.staging_directory(project_id) as staging_directory:
            staged_content = staging_directory / "content.png"
            staged_thumbnail = staging_directory / "thumbnail.png"
            if run_connector:
                job_inputs = dict(inputs)
                job = self.jobs.create_job(
                    project_id,
                    workflow_id=ctx.workflow.id,
                    run_id=ctx.run.id,
                    node_id=ctx.node.id,
                    character_id=character.id,
                    connector_id=ctx.node.connector_id,
                    parameters=ctx.node.parameters,
                    inputs=job_inputs,
                )
                ctx.job_ids.append(job.id)
                result = self.jobs.run_job(project_id, job)
                shutil.move(result.output_path, staged_content)
            else:
                source_text = inputs.get("image")
                if not source_text:
                    raise ValueError("publishing requires an input image")
                shutil.copy2(Path(source_text), staged_content)

            image_info = self.thumbnails.inspect_and_create(
                staged_content,
                staged_thumbnail,
            )
            asset_id = uuid4()
            directory = self._kind_directory(kind)
            relative_path = (
                f"characters/{character.slug}/{directory}/{asset_id}"
                f"{image_info.canonical_extension}"
            )
            thumbnail_relative_path = f"thumbnails/{asset_id}.png"
            asset = Asset(
                id=asset_id,
                kind=kind,
                relative_path=relative_path,
                thumbnail_relative_path=thumbnail_relative_path,
                media_type=image_info.media_type,
                width=image_info.width,
                height=image_info.height,
            )
            updated = self.assets.register_asset(
                project_id,
                character.id,
                expected_revision=character.revision,
                asset=asset,
                staged_content_path=staged_content,
                staged_thumbnail_path=staged_thumbnail,
            )
        ctx.current_character = updated
        return {"image": str(ctx.project_directory / asset.relative_path)}

    @staticmethod
    def _run_selection(ctx: NodeContext) -> dict[str, Any]:
        character = ctx.current_character
        if character is None or character.selected_asset_id is None:
            return {"image": None}
        selected = next(
            (
                asset
                for asset in character.assets
                if asset.id == character.selected_asset_id
            ),
            None,
        )
        if selected is None:
            return {"image": None}
        return {"image": str(ctx.project_directory / selected.relative_path)}

    @staticmethod
    def _kind_directory(kind: AssetKind) -> str:
        return {
            AssetKind.GENERATION: "generations",
            AssetKind.UPSCALE: "upscales",
            AssetKind.EXPORT: "exports",
        }[kind]

    @staticmethod
    def _resolve_inputs(
        workflow: Workflow,
        node: WorkflowNode,
        node_outputs: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for edge in workflow.edges:
            if edge.target_node_id != node.id:
                continue
            source_outputs = node_outputs.get(edge.source_node_id, {})
            if edge.source_port in source_outputs:
                inputs[edge.target_port] = source_outputs[edge.source_port]
        return inputs

    @staticmethod
    def _topological_order(workflow: Workflow) -> list[WorkflowNode]:
        nodes = {node.id: node for node in workflow.nodes}
        in_degree: dict[str, int] = {node.id: 0 for node in workflow.nodes}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in workflow.edges:
            if edge.target_node_id not in nodes or edge.source_node_id not in nodes:
                continue
            if edge.target_node_id not in adjacency[edge.source_node_id]:
                adjacency[edge.source_node_id].append(edge.target_node_id)
                in_degree[edge.target_node_id] += 1
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        order: list[WorkflowNode] = []
        while queue:
            current = queue.pop()
            if current in nodes:
                order.append(nodes[current])
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order
