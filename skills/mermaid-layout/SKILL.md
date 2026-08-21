---
name: mermaid-layout
description: Optimize Mermaid diagram topology for readable, stable rendering with fewer crossings while preserving every business node, edge, label, and semantic. Use this skill whenever creating, generating, rewriting, or substantially modifying Mermaid flowchart, graph, stateDiagram, sequenceDiagram, architecture, dependency, control-flow, or module-interaction diagrams—even when layout optimization is not explicitly requested.
metadata:
  category: visualization
  tags: mermaid, diagrams, graph-layout
---

# Mermaid Layout Skill

## Trigger

Load this skill before creating or substantially editing a Mermaid diagram. Do not wait for an explicit request to “optimize the layout.”

## Role

Act as a Mermaid topology and layout planner. Abstract the graph first, choose renderer-compatible constraints second, and emit Mermaid code third.

## Goal

Make the primary business flow immediately readable while minimizing crossings, long edge spans, branch scattering, and visual noise. Business correctness outranks visual optimization.

## Mermaid rendering model

Mermaid is declarative: a layout engine computes coordinates from graph topology and constraints. Flowchart/`graph` diagrams commonly use dagre; ELK may be selected or configured in supported Mermaid versions. Exact behavior depends on Mermaid version, diagram type, configuration, and renderer.

Therefore:

- Treat source declaration order as a weak tie-breaker and readability aid, never as absolute positioning.
- Do not assume an edge will stay peripheral merely because it is declared last.
- Optimize ranks, direction, explicit semantic grouping, edge locality, and graph scope—not textual order alone.
- Use layout-only relationships only when the target renderer supports them and their meaning is unambiguous.
- If rendering is available, inspect the rendered result; the source is not proof of visual quality.

## Constraints

- Never change business logic, directionality, state meaning, or required relationships for layout.
- Preserve every original business node, edge, label, guard, action, participant, and transition when editing.
- Never merge distinct business nodes or silently omit a relationship.
- Never invent a business relationship through a layout helper.
- Never add dummy, spacer, placeholder, or “alignment” business nodes.
- Preserve user-specified labels unless explicitly asked to rename them.

## Workflow

### Internal layout plan

Complete this plan before writing Mermaid. Keep it internal unless the user asks to see it.

1. **Scope and inventory** — choose the Mermaid type; list sources, sinks, nodes, edges, labels, decisions, loops, domains, and abstraction levels. Distinguish business edges from notes/references.
2. **Ranks** — assign conceptual layers, not pixel coordinates: source/input, main processing stages, fan-out branches, convergence, output/sink. Put recovery paths on adjacent outer ranks where possible. Ranks are planning constraints, not guaranteed renderer positions.
3. **Spine** — select the most important end-to-end path and keep it continuous. A pipeline or embedded stack often follows `Application → Service → Manager/Arbiter → Driver → Hardware`.
4. **Topology hotspots** — mark fan-out, fan-in, hub nodes, cross-layer dependencies, cycles, retries, timeouts, rollback, recovery, and reset paths. Keep each hotspot’s local neighborhood together.
5. **Edge priority** — classify every edge:
   - **P0 main flow:** primary business execution/data path; visual priority.
   - **P1 dependency:** necessary secondary relationship; keep near its endpoints.
   - **P2 exception/recovery:** retry, timeout, failure, rollback, fallback, abort, reset; route around the perimeter.
   - **P3 reference/note:** explanatory or non-control relationship; visually subordinate and never allowed to obscure P0.
6. **Direction** — prefer `LR` for pipelines, sequential stages, and state lifecycles; prefer `TD` for hierarchies and decision trees. Choose the direction that best serves P0 and branch locality, not the previous direction by default.
7. **Scope check** — use an overview + detail diagrams when the graph is likely to remain noisy: roughly more than 20 nodes, 30 business edges, or 4 abstraction levels is a review trigger, not a hard limit. If the user requires one diagram, preserve completeness and state the density trade-off; never omit edges silently.
8. **Semantic boundaries** — add only real subgraphs/groups such as Application, Service, Driver, Network, Storage, Cloud, Device, Bootloader, or DFU. Do not use boundaries as coordinate hacks.
9. **Emission order** — write P0 spine, local P1 branches, convergence, then P2/P3 relationships. This helps weak source-order heuristics but does not replace topology design.
10. **Quality gate** — evaluate the planned/rendered graph before returning it; revise direction, scope, or semantic grouping before considering layout helpers.

## Diagram-type rules

### `flowchart` / `graph`

- Use the rank and spine plan directly; keep branches adjacent to their decision or hub.
- Place fan-in close to its branch endpoints and avoid a giant central hub with unrelated traffic.
- Use `subgraph` only for real ownership, runtime, deployment, or architectural boundaries.

### `stateDiagram` / `stateDiagram-v2`

- Model lifecycle phases explicitly: initialization/boot, operational states, update/DFU, shutdown, and terminal states as applicable.
- Put the normal lifecycle path first and keep its transitions easy to follow.
- Keep fault, timeout, retry, recovery, reset, and abort transitions on the outer side of the lifecycle; preserve guards and transition actions.
- Use a composite state only for a genuine lifecycle or ownership boundary containing multiple substates, such as `Boot`, `Operational`, or `FirmwareUpdate`; never use one solely to force alignment.
- Do not duplicate a semantic state or add placeholder states to improve spacing. If one state machine covers unrelated lifecycles or too many abstraction levels, split overview and detail diagrams.

### `sequenceDiagram`

- Treat participant order and message chronology as the main layout controls; this is not a rank-based graph.
- Declare caller/callee participants in interaction order, group real subsystem participants together, and minimize request/response backtracking.
- Keep the normal exchange as the primary sequence. Use `alt`, `opt`, and `loop` for local branching, retries, and failures near the message that causes them.
- Use `box` only for a genuine subsystem boundary. Do not add fake participants or messages for alignment.
- If the goal is static module topology rather than time-ordered interaction, use `flowchart` or `architecture` instead.

### `architecture-beta`

- Use it for real deployment/runtime architecture: services, devices, networks, storage, and hardware boundaries.
- Group components by actual ownership or deployment boundary. Keep the dominant layer direction stable; for embedded systems prefer `Application → Service → Manager/Arbiter → Driver → Hardware` when that reflects reality.
- Keep normal data/control paths visually primary; place recovery, timeout, error, and reset connections at the perimeter where the syntax and renderer permit.
- Do not create nested groups merely to influence coordinates. Use a flowchart when the requested relationships or renderer support do not fit architecture syntax clearly.

## `subgraph` rules

Use a subgraph when it represents a real boundary, contains multiple related nodes, and reduces ambiguity about ownership or deployment. Do not use it for a single node, cosmetic boxing, artificial rank control, or unrelated declarations. Avoid excessive nesting: one boundary should not contain several invented layout layers. A subgraph is a semantic constraint, not a guaranteed position or edge-routing command.

## Anti-patterns

Reject these approaches and redesign the topology:

- Dummy/spacer nodes or meaningless business nodes created for layout.
- A giant center hub that hides distinct modules or creates many crossings.
- Overusing subgraphs, especially layout-only or deeply nested ones.
- Randomly interleaving declarations and edges from unrelated neighborhoods.
- Relying on source order, invisible edges, or “declare it last” as the primary layout mechanism.
- One diagram mixing too many abstraction levels or unrelated lifecycles.
- Replacing a required edge with an easier-looking shortcut.
- Hiding exception paths in the center of the normal flow.

## Editing existing Mermaid

Preserve the complete semantic inventory first. Then try, in order: reorder local declarations/edges, change `LR`/`TD` or type-appropriate direction, add genuine subgraphs/groups, and only lastly add sparse supported layout-only relationships. For `stateDiagram`, preserve states and transitions; for `sequenceDiagram`, preserve participants, message order, guards, and fragments. Never solve a crossing by changing meaning.

## Quality assessment

Before output, score each item pass/fail:

- Is the P0 spine obvious without tracing every edge?
- Are sibling branches and their downstream nodes locally grouped?
- Are fan-in points close to their branch endpoints?
- Are hubs bounded and long-distance edges limited?
- Are P2/P3 paths peripheral and visually subordinate?
- Do subgraphs/groups represent real boundaries?
- Is the graph free of unnecessary visual noise and mixed abstraction levels?

If any item fails, first change topology, direction, semantic scope, or diagram type. If complexity remains high, split into overview + detail. Do not weaken business semantics to make the score pass.

## Output

Return clean Mermaid code directly when a Mermaid diagram is requested. Keep explanatory comments out of the diagram unless specifically useful. If a split is warranted, say so briefly and provide the requested overview/detail scope without silently dropping relationships. Prefer readable source order, but never imply that source order guarantees renderer placement.
