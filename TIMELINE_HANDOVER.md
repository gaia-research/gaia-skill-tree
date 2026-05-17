# Handover: Timeline/History Tracking for Gaia Skill Trees and Skills

This document details the newly added timeline feature, which tracks meta-changes to skills and user skill trees. The feature was designed based on the requirements and the ubiquitous language detailed in `CONTEXT.md`.

## Changes Introduced

1. **Schemas Updated:**
   - **`registry/schema/skillTree.schema.json`**: An optional `timeline` property was added. It holds an array of `timelineEvent` objects that track meta-changes on a user's skill tree.
   - **`registry/schema/skill.schema.json`**: An optional `timeline` property was added. It holds an array of `timelineEvent` objects that track the evolution of a canon skill.

2. **CLI Tools Updated:**
   - Introduced `src/gaia_cli/timeline.py` which provides helper functions (`append_skill_tree_event` and `append_skill_event`) for pushing events into the arrays.
   - Modifed CLI commands (`promote`, `fuse`, `propose`, `push`) to use the appropriate ubiquitous verbs (`rank_up`, `fuse`, `propose`, `name`, `ascend`, etc.) to log events whenever they happen.

## Frontend Usage & Consumption

During static generation (or dynamic rendering) on the frontend, you can easily parse these `timeline` fields to render beautiful chronological feeds for both User Pages and Skill Pages.

### 1. User Timeline (Skill Tree)
The user's `skillTree.json` file (typically found under `skill-trees/{username}/skill-tree.json`) now optionally contains a `timeline` array:
```json
{
  "userId": "garrytan",
  "updatedAt": "2023-11-01T12:00:00Z",
  "timeline": [
    {
      "timestamp": "2023-11-01T10:15:30Z",
      "action": "push",
      "skillId": "autonomous-debug",
      "details": "Pushed in batch proposal-autonomous-debug-..."
    },
    {
      "timestamp": "2023-11-02T14:22:11Z",
      "action": "rank_up",
      "skillId": "autonomous-debug",
      "details": "Leveled up from 1★ to 2★"
    },
    {
      "timestamp": "2023-11-05T09:44:00Z",
      "action": "fuse",
      "skillId": "code-review-pipeline",
      "details": "Fused from browser-automation, code-generation"
    }
  ]
}
```
**Frontend Idea:** Use this array to render an activity feed or timeline diagram on the "Your Tree" / Profile page. The action verb allows you to map specific icons or colors to the events (e.g. `rank_up` gets a star icon, `fuse` gets an intersection icon).

### 2. Skill Evolution Timeline (Canon)
Each skill file (inside `registry/gaia.json` or individually constructed skill files) may contain a `timeline` array capturing the canonical evolution:
```json
{
  "id": "autonomous-debug",
  "name": "Autonomous Debug",
  "timeline": [
    {
      "timestamp": "2023-11-03T11:00:00Z",
      "action": "name",
      "contributor": "garrytan",
      "details": "Named by @garrytan as garrytan/autonomous-debug"
    },
    {
      "timestamp": "2023-11-10T16:00:00Z",
      "action": "rank_up",
      "details": "Promoted to unique skill"
    }
  ]
}
```
**Frontend Idea:** Render an "Ascension Cycle" history on the individual Skill page. This provides transparent history of when it was named, when it ranked up, and who contributed to its growth.

## The Action Vocabulary

Here are the vocabulary terms (from `CONTEXT.md`) that will appear under `action`:

- `rank_up`: A skill moves up in stars (level).
- `ascend`: A skill hits 6★ Transcendent ★.
- `fuse`: A skill is created from prerequisites.
- `propose`: A contributor claims an ultimate skill.
- `name`: A skill reaches 2★ and attaches an Origin Contributor.
- `demote`: A skill drops back a star level due to retraction or demerit.
- `push`: A batch of skills was submitted.
- `bond`: An agent links via MCP.
- `register`: A repo first initialized Gaia.

You can safely base UI logic (such as icons, color glow filters based on DESIGN.md) off of this action enum.
