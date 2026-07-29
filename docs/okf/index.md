---
okf_version: "0.1"
---

# Gaia Skill Tree OKF Bundle

Welcome to the agent-readable Open Knowledge Format (OKF) bundle of the Gaia Skill Tree registry.

## Registry Index

### Basic Skills (121)

* [API Call](/skills/basic/api-call.md) - A fundamental skill that enables agents to interact with external services via HTTP API calls.
* [Adaptive Pattern Learning](/skills/basic/adaptive-pattern-learning.md) - Implements adaptive learning through pattern recognition and strategy optimization.
* [Agent Reach](/skills/basic/agent-reach.md) - Gives an AI agent internet access by routing web requests across 16+ platforms with MCP support and harness-agnostic integration.
* [Audience Model](/skills/basic/audience-model.md) - Adapts tone, complexity, and framing of output to match a target audience profile.
* [Auto-Review](/skills/basic/auto-review.md) - Automatically review and gate agent outputs by writing and executing a self-authored acceptance script, combining self-critique with pre-completion verification.
* [Autonomous Engineering Platform](/skills/basic/autonomous-engineering-platform.md) - An autonomous engineering platform integrating chat, specs, tasks, and code for full agentic software delivery.
* [Bioinformatic Sequence Analysis](/skills/basic/bioinformatic-sequence-analysis.md) - Performs biological sequence alignment, similarity searches, multiple sequence alignment (MSA), and genomic variant analysis using standard bioinformatics tools and databases.
* [Browser Control](/skills/basic/browser-control.md) - A foundational skill for interacting directly with the web browser using Chrome DevTools Protocol (CDP).
* [CI Churn Analysis](/skills/basic/ci-churn-analysis.md) - Measures avoidable CI iteration cost for a pull request by classifying commits as feature work versus fix-the-CI rework, summing CI compute time burned on avoidable push rounds, and surfacing pre-push checks that would have prevented them.
* [CLI Modernization](/skills/basic/cli-modernization.md) - Refactors command-line interfaces for improved UX, plugin architecture, and extensibility.
* [CRM Data Cleanup](/skills/basic/crm-data-cleanup.md) - Perform data hygiene, normalization, and deduplication of contact, event, or organization records in CRM and tracking databases.
* [Chain-of-Thought Reasoning](/skills/basic/chain-of-thought.md) - Produces explicit intermediate reasoning steps before arriving at a final answer, dramatically improving accuracy on multi-step problems.
* [Chunk Document](/skills/basic/chunk-document.md) - Splits a document into semantically meaningful segments optimized for embedding and retrieval.
* [Cite Sources](/skills/basic/cite-sources.md) - Attributes claims to specific sources with proper references, URLs, or bibliographic entries.
* [Classify](/skills/basic/classify.md) - Assigns one or more categorical labels to an input based on learned or rule-based criteria.
* [Clinical Data Retrieval](/skills/basic/clinical-data-retrieval.md) - Retrieves and parses clinical trial records, drug approvals, regulatory filings, or medical variant databases (e.g. ClinicalTrials.gov, OpenFDA, ClinVar).
* [Code Execution](/skills/basic/code-execution.md) - Writes and executes code in a sandboxed environment, uses the runtime output to verify correctness, and iterates until the result is correct.
* [Code Explain](/skills/basic/code-explain.md) - Generates accurate natural-language explanations of source code, describing intent, logic flow, and key decisions at function or module level.
* [Code Generation](/skills/basic/code-generation.md) - Produces syntactically correct and functionally appropriate source code from specifications or prompts.
* [Computer Use](/skills/basic/computer-use.md) - Controls desktop GUIs and web browsers by interpreting screenshots, issuing mouse/keyboard actions, and verifying visual state to complete open-ended computer tasks.
* [Context Compression](/skills/basic/context-compression.md) - Reduces the length of prompts or retrieved context to fit token limits while preserving semantic content, using techniques such as selective token removal, summarization, or token-classification-based pruning (e.g. LLMLingua).
* [Core Platform Implementation](/skills/basic/core-platform-implementation.md) - Implements foundational platform architecture including plugin discovery, server lifecycle management, and API contracts.
* [Cultural Localization](/skills/basic/cultural-localization.md) - Adapts content for regional audiences beyond translation: idioms, cultural nuance, tone, trust conventions, and regional compliance for culturally faithful output.
* [Data Visualize](/skills/basic/data-visualize.md) - Generates charts, graphs, and visual summaries from datasets by selecting appropriate visualization types and mapping data dimensions.
* [Diff Content](/skills/basic/diff-content.md) - Compares two versions of content and produces a structured delta highlighting additions, deletions, and modifications.
* [Document Editing](/skills/basic/document-editing.md) - Reads, edits, repacks, and applies styling or design principles to structured binary document formats such as PPTX, DOCX, and XLSX.
* [Domain Modeling](/skills/basic/domain-modeling.md) - Build and maintain a shared domain model with ubiquitous language and architectural decision records.
* [Embed Text](/skills/basic/embed-text.md) - Converts text into dense vector representations suitable for similarity search and clustering.
* [Error Interpretation](/skills/basic/error-interpretation.md) - Diagnoses error messages, stack traces, and failure modes to identify root causes and suggest fixes.
* [Evaluate Output](/skills/basic/evaluate-output.md) - Assesses the quality, correctness, or safety of generated output against defined criteria.
* [Event Attendance Metrics](/skills/basic/event-attendance-metrics.md) - Collect, process, and query attendee RSVP and check-in records for events, normalizing data to produce clean, unique attendance counts and metrics.
* [Event Attendee Management](/skills/basic/event-attendee-management.md) - Manage, export, sync, and format event attendee data between registration platforms, CRM databases, and spreadsheet records.
* [Event Support Triage](/skills/basic/event-support-triage.md) - Triage customer support emails or issues related to events, query attendee records to address ticketing problems, and draft responses using dynamic templates.
* [Event Ticket Transfer](/skills/basic/event-ticket-transfer.md) - Process requests to transfer event tickets between attendees, validating tickets, updating registration metadata, and resending confirmation passes.
* [Extract Entities](/skills/basic/extract-entities.md) - Identifies and extracts named entities such as people, organizations, dates, and locations from text.
* [Feed Monitoring](/skills/basic/feed-monitoring.md) - Monitors RSS, Atom, blog, or other recurring content feeds, discovers updates, tracks read state, and surfaces new signals for downstream agent workflows.
* [Few-Shot Learning](/skills/basic/few-shot-learning.md) - Conditions a language model on a small number of input-output demonstrations within the prompt, enabling task adaptation without weight updates.
* [Fine-Tune](/skills/basic/fine-tune.md) - Adapts a pre-trained model to a new task or domain by updating model weights using parameter-efficient methods such as LoRA, QLoRA, or full supervised fine-tuning, without retraining from scratch.
* [Format Output](/skills/basic/format-output.md) - Structures raw output into a specified format such as markdown, JSON, CSV, or HTML.
* [Framework Upgrade](/skills/basic/framework-upgrade.md) - Guides an agent through upgrading a project from one major framework version to another, including breaking-change detection, migration steps, and post-upgrade validation.
* [Generate SQL](/skills/basic/generate-sql.md) - Translates natural-language data questions into syntactically correct, executable SQL queries against a given schema.
* [Generate Test](/skills/basic/generate-test.md) - Produces comprehensive unit, integration, and edge-case test suites from source code.
* [Generate Text](/skills/basic/generate-text.md) - Produces coherent natural language output given a prompt, instruction, or context window.
* [Genomic Data Retrieval](/skills/basic/genomic-data-retrieval.md) - Queries and retrieves DNA sequence data, transcription factor binding models, cis-regulatory elements, and genetic annotations from genomic repositories (e.g. Ensembl, GTEx, JASPAR, UniBind, ENCODE, UCSC, dbSNP).
* [Git Diff Risk Analysis](/skills/basic/git-diff-risk-analysis.md) - Analyzes git diffs for complexity, churn, and risk scores to prioritize review attention and flag dangerous changes.
* [Grant Application Processing](/skills/basic/grant-application-processing.md) - Process financial aid, grant, or assistance applications by calculating discounts, assigning discount codes, updating tracker logs, and sending status updates.
* [Headless Worker Collect](/skills/basic/headless-worker-collect.md) - Aggregates and formats results from distributed headless workers stored in shared memory with filtering and status reporting.
* [Headless Worker Spawn](/skills/basic/headless-worker-spawn.md) - Launches headless AI worker processes for parallel background task execution with configurable worker types and shared memory coordination.
* [Hybrid Workflow Coordination](/skills/basic/hybrid-workflow-coordination.md) - Routes tasks between interactive reasoning phases and parallel background execution with configurable workflow templates.
* [Hypothesis Generation](/skills/basic/hypothesis-generate.md) - Formulates novel, testable scientific hypotheses by synthesising existing literature, identifying knowledge gaps, and proposing mechanistic explanations.
* [Image Caption](/skills/basic/image-caption.md) - Generates accurate natural-language descriptions of images, capturing objects, actions, and spatial relationships.
* [Image Generate](/skills/basic/image-generate.md) - Creates photorealistic or stylized images from text prompts using diffusion-based or autoregressive generative models.
* [Issue Triage](/skills/basic/issue-triage.md) - Classifies incoming issue reports through a structured state machine, assigns triage roles (bug/enhancement, needs-info/ready-for-agent/wontfix), reproduces bugs, requests missing detail, and produces structured resolution briefs for agent or human handoff.
* [Literature Search](/skills/basic/literature-search.md) - Queries and searches academic literature databases (e.g. PubMed, arXiv, bioRxiv, OpenAlex) to locate papers, retrieve abstracts, resolve citations, and fetch full-text documents.
* [Logical Inference](/skills/basic/logical-inference.md) - Applies deductive, inductive, or abductive reasoning to derive valid conclusions from premises and structured knowledge.
* [MCP Integration](/skills/basic/mcp-integration.md) - Connect to and invoke tools exposed by Model Context Protocol (MCP) servers — enumerate available tools, execute calls, and handle responses across any MCP-compatible backend.
* [Math Reason](/skills/basic/math-reason.md) - Solves multi-step mathematical problems including arithmetic, algebra, calculus, and competition mathematics through symbolic and numeric reasoning.
* [Memory Pattern Design](/skills/basic/memory-pattern-design.md) - Designs recurring memory storage patterns for AI agents with LRU caching, SQLite persistence, and associative retrieval.
* [Molecular Databases](/skills/basic/molecular-databases.md) - Queries and retrieves structural, chemical, and biological activity data for small molecules, chemical compounds, or drug candidates from molecular repositories (e.g., ChEMBL, PubChem).
* [Multi-Repo Coordination](/skills/basic/multi-repo-coordination.md) - Manages synchronized operations across multiple repositories including cross-repo PRs, dependency tracking, and bulk workflow automation.
* [OCR](/skills/basic/optical-character-recognition.md) - Extracts machine-readable text from raster images, scanned pages, and photo documents using optical character recognition, preserving layout and handling skew, noise, and varied fonts.
* [Object Detection](/skills/basic/object-detection.md) - Locates and classifies multiple objects within images by producing bounding boxes, confidence scores, and category labels in a single forward pass.
* [Opinion](/skills/basic/opinion.md) - Formulate and articulate a strong, reasoned opinion or recommendation as a discrete agent step, avoiding model selection bias and decision paralysis.
* [Parallel Execution](/skills/basic/parallel-execution.md) - Decompose a task into independent sub-tasks and execute them concurrently, merging results with configurable concurrency limits and queue-based state tracking.
* [Parse HTML](/skills/basic/parse-html.md) - Extracts structured content from raw HTML, navigating DOM trees and handling malformed markup.
* [Parse JSON](/skills/basic/parse-json.md) - Extracts structured data from JSON-formatted input, handling nested objects and arrays.
* [Parse PDF](/skills/basic/parse-pdf.md) - Extracts text, tables, equations, and structure from PDF documents, preserving layout and reading order.
* [Pathway Ontology Retrieval](/skills/basic/pathway-ontology-retrieval.md) - Queries, parses, and resolves biological pathway models, cellular reactions, and hierarchical ontology metadata from pathway and ontology search systems (e.g., Reactome, QuickGO, EMBL-EBI OLS).
* [Performance Tuning](/skills/basic/performance-tuning.md) - Profiles execution hotspots, measures throughput and latency, and applies targeted optimizations to reduce resource consumption.
* [Plan Synthesis](/skills/basic/plan-synthesis.md) - Combine two or more independently produced plans into a single attributed result, resolving conflicts and surfacing consensus and divergence.
* [Plan and Decompose](/skills/basic/plan-decompose.md) - Breaks a complex objective into an ordered sequence of executable sub-tasks.
* [Probabilistic Programming](/skills/basic/probabilistic-programming.md) - Specifies Bayesian models and runs inference (MCMC/NUTS, variational) to quantify epistemic and aleatoric uncertainty using PyMC, Stan, Pyro, or NumPyro.
* [Prompt Injection Defense](/skills/basic/prompt-injection-defense.md) - Detects and neutralizes adversarial instructions injected into agent context from untrusted external sources (indirect prompt injection), using techniques such as context isolation, hierarchical intent verification, or semantic consistency checks.
* [Protein Structure Analysis](/skills/basic/protein-structure-analysis.md) - Analyzes, searches, and aligns three-dimensional macromolecular structures using structural databases, alignment search algorithms (e.g. Foldseek, PDB search), or molecular modeling tools.
* [Proteomic Data Retrieval](/skills/basic/proteomic-data-retrieval.md) - Queries and retrieves amino acid sequences, protein families, functional domains, tissue distribution, and protein-protein interactions from proteomic repositories (e.g. UniProt, InterPro, Human Protein Atlas, STRING).
* [Question Answer](/skills/basic/question-answer.md) - Produces accurate, context-grounded answers to natural-language questions, handling unanswerable cases.
* [Rank](/skills/basic/rank.md) - Orders a set of candidate items by relevance, quality, or fitness for a given objective.
* [React Performance Optimization](/skills/basic/react-performance-optimization.md) - Optimizes component rendering, data fetching, and bundle composition in React applications while preserving requested behavior.
* [Refactor Code](/skills/basic/refactor-code.md) - Restructures existing source code to improve readability, maintainability, or performance without changing observable behavior.
* [Requirements Analysis](/skills/basic/requirements-analysis.md) - Elicit and structure requirements from stakeholder inputs into formal specifications — user stories, acceptance criteria, and traceability matrices.
* [Retrieve](/skills/basic/retrieve.md) - Fetches relevant documents or passages from an indexed corpus given a query.
* [Reward Modeling](/skills/basic/reward-modeling.md) - Learns a scalar reward signal from human preference comparisons between model outputs, enabling reinforcement learning from human feedback (RLHF) to align model behavior with human values.
* [Route Intent](/skills/basic/route-intent.md) - Classifies user intent and directs execution to the appropriate handler, tool, or sub-agent.
* [Schema Design](/skills/basic/schema-design.md) - Design database schemas across relational, NoSQL, graph, and time-series stores — entity modelling, normalization, indexing strategies, and migration planning.
* [Scientific Visualization](/skills/basic/scientific-visualization.md) - Creates publication-ready scientific figures and visualizes molecular structures.
* [Score Relevance](/skills/basic/score-relevance.md) - Assigns a numerical relevance score to candidate items relative to a query or objective.
* [Scroll World](/skills/basic/scroll-world.md) - Builds scroll-scrubbed 3D world landing pages for any brand or industry with zero-cut camera paths through connected scenes.
* [Self-Consistency](/skills/basic/self-consistency.md) - Samples multiple independent reasoning paths for the same problem and selects the answer by majority vote, improving robustness without any additional training.
* [Self-Critique](/skills/basic/self-critique.md) - Iteratively evaluates and refines its own outputs using self-generated feedback, improving quality without external supervision.
* [Semantic Cache](/skills/basic/semantic-cache.md) - Stores LLM responses keyed by embedding similarity so that semantically equivalent queries are served from cache, reducing inference latency and token cost without sacrificing answer quality.
* [Sentiment Analysis](/skills/basic/sentiment-analysis.md) - Classifies the affective polarity (positive / negative / neutral, or fine-grained) of user-generated text. Covers pipelines from raw noisy input through preprocessing, inference (Transformer, Lexicon, or LLM), and output normalisation.
* [Sequential Agent Pipeline](/skills/basic/sequential-agent-pipeline.md) - Chains agent outputs sequentially so each step's result feeds the next, enabling multi-stage data transformation and coordinated processing.
* [Skill Discovery](/skills/basic/skill-discovery.md) - Searches a skill or tool registry, ranks results by relevance and install count, and surfaces candidates for the agent to adopt or invoke.
* [Software Design](/skills/basic/software-design.md) - Design software modules with clean interfaces, seams, and deep implementations for maintainability and testability.
* [Speech to Text](/skills/basic/speech-to-text.md) - Transcribes spoken audio into accurate text, handling diverse accents, noise conditions, and multiple languages.
* [Static Artwork Design](/skills/basic/static-artwork-design.md) - Creates original static visual artifacts such as posters and print-ready graphics from a design brief.
* [Statistical Analysis](/skills/basic/statistical-analysis.md) - Performs hypothesis testing, regression analysis, and Bayesian modelling with effect size calculation and APA-formatted statistical reporting using scipy, statsmodels, and PyMC.
* [Structured Output Generation](/skills/basic/structured-output.md) - Generates output guaranteed to conform to a given schema (JSON, YAML, Pydantic model, etc.) using constrained decoding or grammar-guided generation.
* [Summarize](/skills/basic/summarize.md) - Condenses longer input into a shorter representation that preserves key information and intent.
* [Swarm Topology Management](/skills/basic/swarm-topology-management.md) - Initializes and manages multi-agent swarm network topologies (hierarchical, mesh, ring, star) with load balancing and fault tolerance.
* [Synthetic Data Generation](/skills/basic/synthetic-data-generation.md) - Generates privacy-preserving, domain-representative datasets via tabular synthesis and generative models, infusing schema and regulatory constraints to substitute for sensitive real data.
* [System Integration](/skills/basic/system-integration.md) - Connects disparate subsystems via shared contracts, event buses, and compatibility layers for coherent cross-component operation.
* [Test-Driven Development](/skills/basic/test-driven-development.md) - Enforces a strict red-green-refactor TDD loop: writes failing tests before implementation, blocks code generation that skips the test step, and validates coverage thresholds before marking tasks complete.
* [Text to Speech](/skills/basic/text-to-speech.md) - Synthesizes natural-sounding speech audio from text input, supporting voice cloning and prosody control.
* [Time Series Forecasting](/skills/basic/time-series-forecasting.md) - Forecasts temporal sequences with seasonal-trend decomposition, ensemble models (ARIMA, Prophet, NBEATS, TFT), and residual-based anomaly detection.
* [Token Observability](/skills/basic/token-observability.md) - Observability tool for tracking AI coding agent token spend locally.
* [Tokenize](/skills/basic/tokenize.md) - Splits input text into discrete tokens suitable for downstream processing by language models.
* [Tool Select](/skills/basic/tool-select.md) - Chooses the most appropriate tool or API from a set of available options given a task description.
* [Tool Use](/skills/basic/tool-use.md) - Invokes external functions or APIs by generating well-formed call signatures, parsing results, and incorporating them into reasoning.
* [Transactional Email Resend](/skills/basic/transactional-email-resend.md) - Manage and resend transactional ticket or confirmation emails, verifying recipient addresses and utilizing rate-limited or alternative relays to ensure delivery.
* [Translate](/skills/basic/translate.md) - Converts text from one natural language to another while preserving meaning, tone, and formatting.
* [UI Audit](/skills/basic/ui-audit.md) - Structured review of a product's user interface for layout clarity, affordance, accessibility, and visual polish — produces actionable improvement recommendations.
* [UX Audit](/skills/basic/ux-audit.md) - Systematically evaluates a user interface against established usability heuristics or accessibility standards, producing a scored finding report with remediation recommendations.
* [Vector DB Optimization](/skills/basic/vector-db-optimization.md) - Tunes vector database indices, sharding strategies, and multi-database coordination for production-scale retrieval.
* [Vector Search](/skills/basic/vector-search.md) - Performs similarity search over high-dimensional embeddings using cosine, Euclidean, dot-product, or custom distance metrics.
* [Visual Question Answering](/skills/basic/vision-qa.md) - Answers natural-language questions grounded in a specific image or screenshot by combining visual perception with language reasoning, enabling visual debugging, UI analysis, and document-image Q&A.
* [Web Search](/skills/basic/web-search.md) - Queries external search engines or APIs and retrieves relevant result sets.
* [Worker Agent Dispatch](/skills/basic/worker-agent-dispatch.md) - Maps trigger events to optimal agent combinations for background task execution with performance tracking and continuous feedback.
* [Write Report](/skills/basic/write-report.md) - Produces structured, multi-section written output with headings, citations, and coherent narrative.
* [evidence-attestation](/skills/basic/evidence-attestation.md) - Produces privacy-safe proof objects from agent claims by recording what evidence supports or contradicts each claim, what raw content was intentionally omitted, what verdict follows, and what would make the evidence stale; enables downstream registries, review gates, and scoreboards to verify agent work without accessing raw private context.
* [implement-with-discernment](/skills/basic/implement-with-discernment.md) - Applies deliberate judgment before writing code: evaluating whether to implement at all, scoping to the minimum needed, deferring or rejecting features that add complexity without proportionate value, and stopping when the task is done.

