import json
import os
from datetime import datetime

def patch_gaia():
    gaia_path = 'registry/gaia.json'
    with open(gaia_path, 'r', encoding='utf-8') as f:
        gaia = json.load(f)

    new_skills = [
        {
            "id": "generative-media",
            "name": "Generative Media",
            "type": "extra",
            "level": "3\u2605",
            "description": "Generates and manipulates images, video, and audio through complex node-based or scripted generative workflows, managing model dependencies and parameter injection.",
            "prerequisites": ["data-visualize"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "B",
                    "source": "https://github.com/comfyanonymous/ComfyUI",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "ComfyUI -- most powerful and modular stable diffusion GUI and backend; node-based graph execution for generative media."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "demerits": ["heavyweight-dependency"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "collaborative-diagramming",
            "name": "Collaborative Diagramming",
            "type": "extra",
            "level": "2\u2605",
            "description": "Generates and manages digital diagrams, flowcharts, and architecture maps in web-native or collaborative formats, optimized for hand-drawn aesthetics or structured vector output.",
            "prerequisites": ["data-visualize"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "B",
                    "source": "https://github.com/excalidraw/excalidraw",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Excalidraw -- virtual whiteboard for sketching hand-drawn like diagrams; widespread adoption for developer documentation."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "mathematical-animation",
            "name": "Mathematical Animation",
            "type": "extra",
            "level": "3\u2605",
            "description": "Produces programmatic mathematical and algorithmic animations with high pedagogical and visual quality, utilizing LaTeX for notation and geometric coordinate systems for spatial layout.",
            "prerequisites": ["data-visualize"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "B",
                    "source": "https://github.com/ManimCommunity/manim",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Manim Community Edition -- programmatic animation engine for explanatory math videos; inspired by 3Blue1Brown."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "demerits": ["heavyweight-dependency"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "project-management",
            "name": "Project Management",
            "type": "basic",
            "level": "2\u2605",
            "description": "Manages issues, tasks, projects, and team workflows through structured project management platforms, handling state transitions and priority levels.",
            "prerequisites": ["issue-triage"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "C",
                    "source": "https://hermes-agent.nousresearch.com/docs/skills",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Hermes Skills Hub: Linear integration for issue and project management."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "workspace-automation",
            "name": "Workspace Automation",
            "type": "basic",
            "level": "2\u2605",
            "description": "Orchestrates productivity tasks across email, calendar, drive, and documents through unified office suite integrations, automating scheduling and file management.",
            "prerequisites": ["api-call"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "C",
                    "source": "https://hermes-agent.nousresearch.com/docs/skills",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Hermes Skills Hub: Google Workspace integration for unified email, calendar, and drive access."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "knowledge-management",
            "name": "Knowledge Management",
            "type": "basic",
            "level": "2\u2605",
            "description": "Organizes, relates, and retrieves information across structured pages, databases, and shared knowledge bases, maintaining semantic links between information nodes.",
            "prerequisites": ["api-call"],
            "derivatives": ["knowledge-harvest"],
            "conditions": "",
            "evidence": [
                {
                    "class": "C",
                    "source": "https://hermes-agent.nousresearch.com/docs/skills",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Hermes Skills Hub: Notion integration for structured notes and databases."
                }
            ],
            "knownAgents": ["NousResearch/hermes-agent"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        },
        {
            "id": "ml-artifact-management",
            "name": "ML Artifact Management",
            "type": "basic",
            "level": "2\u2605",
            "description": "Manages machine learning models, datasets, and experiment logs through centralized hub or tracking repositories, handling versioning and metadata extraction.",
            "prerequisites": ["api-call"],
            "derivatives": [],
            "conditions": "",
            "evidence": [
                {
                    "class": "B",
                    "source": "https://github.com/huggingface/huggingface_hub",
                    "evaluator": "gemini-cli",
                    "date": "2026-05-17",
                    "notes": "Hugging Face Hub CLI -- standard interface for managing ML artifacts."
                }
            ],
            "knownAgents": ["huggingface/hf-cli"],
            "status": "provisional",
            "createdAt": "2026-05-17",
            "updatedAt": "2026-05-17",
            "version": "0.1.0"
        }
    ]

    gaia['skills'].extend(new_skills)
    gaia['skills'].sort(key=lambda x: x['id'])
    
    with open(gaia_path, 'w', encoding='utf-8') as f:
        json.dump(gaia, f, indent=2, ensure_ascii=False)
    print(f"Added {len(new_skills)} new skills to gaia.json")

def patch_named_skills():
    named_skills_path = 'registry/named-skills.json'
    with open(named_skills_path, 'r', encoding='utf-8') as f:
        named_skills = json.load(f)

    new_named = {
        "id": "stanfordnlp/dspy",
        "name": "DSPy",
        "contributor": "stanfordnlp",
        "origin": True,
        "genericSkillRef": "prompt-optimization",
        "status": "named",
        "level": "3★",
        "description": "Declarative programming of language model pipelines, automatically optimizing prompts and RAG retrieval using bootstrapping and teleprompters.",
        "title": "The Programmatic Prompt Engineer",
        "catalogRef": "stanfordnlp-dspy",
        "tags": ["dspy", "prompt-optimization", "rag", "lm-programs"],
        "links": {
            "github": "https://github.com/stanfordnlp/dspy",
            "arxiv": "https://arxiv.org/abs/2310.03714"
        },
        "role": "origin"
    }

    if "prompt-optimization" not in named_skills["buckets"]:
        named_skills["buckets"]["prompt-optimization"] = []
    
    named_skills["buckets"]["prompt-optimization"].append(new_named)
    
    with open(named_skills_path, 'w', encoding='utf-8') as f:
        json.dump(named_skills, f, indent=2, ensure_ascii=False)
    print("Added stanfordnlp/dspy to named-skills.json")

if __name__ == '__main__':
    patch_gaia()
    patch_named_skills()
