# Intelligent Agent-Based Video Asset Retrieval System Architecture

## 1. SYSTEM OVERVIEW
**Purpose:** 
To provide an automated, reasoning-driven pipeline that ingests spreadsheet-based multimedia link repositories and handles the bulk retrieval, contextual renaming, hierarchical organization, and reporting of video assets across diverse platforms.

**Pipeline Flow:** 
1. **Input:** Microsoft Excel documents (`.xlsx` or `.csv`) containing URLs and associated multimedia metadata (such as campaign tags and video titles).
2. **Transformation:** The dataset is parsed, validated, cleaned, and structurally modeled. A Large Language Model (LLM) classifies links and maps them to appropriate agents and sub-tools.
3. **Execution:** Autonomous agents parallelize and govern the specific executions according to the assigned tools.
4. **Monitoring:** All processing stages emit real-time logs tracking successes and failure modes.
5. **Output:** Downloaded local assets are shifted to a cloud drive (e.g., Google Drive), structured into a hierarchical taxonomy. Summary metrics and error reports are generated.

---

## 2. MODULE BREAKDOWN

**1. Input Layer (Excel Ingestion and URL Extraction Module)**
- Ingests raw spreadsheets using chunked reads allowing scalability (valid up to 1 million rows).
- Analyzes datasets via Regex to extract domain topologies.
- Sanitizes query parameters and explicitly removes absolute duplicates to trim processing overhead.
- Serializes sanitized lists into machine-readable JSON manifests.

**2. Intelligence Layer (LLM Classification and Tool Recommendation Engine)**
- Serves as the cognitive heart of the architecture by consuming the JSON manifest via an API request to a given paradigm-capable LLM.
- Analyzes the URL payload in conjunction with natural language requirements to designate the relevant asset platform (YouTube, Google Drive, direct CDN, etc.).
- Evaluates constraints and prescribes the exact execution tool (e.g., `yt-dlp`) customized for the payload's source topology.

**3. Execution Layer (Autonomous Download Agent Orchestration Framework)**
- Distributes computational responsibilities across multiple bounded autonomous agents.
- Each agent serves as a bounded unit carrying dependencies for a specific source platform.
- Processes chunked arrays of download targets synchronously or asynchronously dependent on tool requirements and authentication necessities.

**4. Monitoring Layer (Task Execution Monitoring / Error Detection Module)**
- Wraps every downstream execution layer with an overarching error-catch state diagram.
- Detects constraints (authorization blockers, rate limits, broken pointers) and relays structured telemetry.
- Records output to a human-readable Google Sheet and a raw programmatic `.jsonl` trace file to support deterministic tracking.

**5. Storage Layer (Cloud Organization and Folder Hierarchy Engine)**
- Maps standard local ingestion directories to structured cloud folder trees.
- Dynamically derives folder paths built upon taxonomy classifications identified by the LLM (e.g., `Root/YouTube/Public/CampaignName`).
- Integrates semantic file-renaming heuristics leveraging original Excel metadata against video dimensions.
- Issues the final programmatic handoff files: `summaryreport.html` and `brokenlinksreport.xlsx`.

---

## 3. DATA FLOW

1. **Upload & Preprocessing:** User provisions Excel data → Regex sanitizes URLs → Duplicates aggregated/eliminated → Data structured into a Master JSON Manifest.
2. **LLM Inference:** JSON Manifest dispatched to the LLM alongside Natural Language User Prompts → System maps domains to semantic classifications and maps specific downloading tools.
3. **Agent Assignment:** A pool of platform-agnostic Agents accepts configurations tailored iteratively to classification topologies.
4. **Execution Cycle:** Designated agents invoke downstream binaries (e.g., `wget`, `gdown`) → Payloads stream into staging environments.
5. **Telemetry Relaying:** Realtime operations funnel stream failures/accomplishments into `.jsonl` records and a Google Sheet.
6. **Delivery & Structure:** Agents move payload binaries to their final destination tree → Nomenclatures replaced dynamically → Final HTML reporting generated spanning workflow efficiencies.

---

## 4. JSON STRUCTURE DESIGN

Design schema representation of the extracted assets mapped against LLM inferred behaviors:

```json
{
  "asset_id": "01H21VKZ49F2D8S",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "metadata": {
    "title": "Marketing Promo Q1",
    "category_tag": "Commercial",
    "acquisition_date": "2026-04-01"
  },
  "classification": {
    "platform": "YouTube",
    "type": "Public",
    "domain_signal": "youtube.com/watch"
  },
  "execution": {
    "agent": "YouTube Agent",
    "tool": "yt-dlp",
    "status": "pending_execution"
  }
}
```

---

## 5. CLASSIFICATION LOGIC

**Platform Taxonomy Rules:**
- **YouTube (Public):** Extracts patterns from generic domains `youtube.com/watch`, `youtu.be`, or `shorts/`.
- **YouTube (Unlisted/Private):** Identifies exact primary domains alongside authenticated token/parameter presence dictating security measures.
- **Google Drive:** Analyzes sequences containing `drive.google.com/file/` or short patterns using `/d/`.
- **Direct MP4 / CDN:** Bypasses proprietary wrappers tracing extensions exclusively matched to media footprints: `.mp4`, `.m3u8`, or `.webm`.

**Reasoning Heuristics:**
- The LLM assesses context bridging (i.e. if an ambiguous CDN acts securely or broadly) matching semantic rules against known behaviors.
- The rule-based engine acts as the foundational baseline (e.g., parsing regex filters), delegating anomaly processing unresolvable parameters to the LLM wrapper when natural language rules are ambiguously stated by the user.

---

## 6. AGENT DESIGN

**Definition:** 
An agent is an isolated microservice logic entity tasked with retrieving a singular type of digital asset utilizing a specialized downstream dependency executable mapping the system input bounds.

**Capabilities:**
- **Encapsulation:** 1-to-1 Mapping (One agent architecture applies specifically to one designated Source/Platform environment).
- **Inputs:** A parsed structured JSON chunk corresponding accurately to its classification topology bounds and user-provided filtering arguments.
- **Outputs:** An asset payload placed inside a local staging target, tagged metadata for the semantic re-namer, and real-time execution heartbeat telemetry mapping pass/fail conditions.
- **Responsibilities:** Maintain state integrity per download task, proxy authentications optimally, retry exponential fallbacks natively for specific tool sets, and funnel deterministic stdout logs to the Monitoring Layer without corruption.

---

## 7. TOOL MAPPING

Based natively on contextual source matching:
- **YouTube (Public / Unlisted / Private):** → `yt-dlp`
- **Google Drive:** → `gdown`
- **External CDN / Direct Payload:** → `Python requests` or `curl/wget` stream implementations.

*(Tools are dynamically linked based on instructions passed iteratively within the LLM generated plan)*

---

## 8. PIPELINE DESIGN

**Step-by-Step Architecture Pipeline Flow:**

1. `DataProcessor()`: Read bytes from Excel, detect URL strings, drop duplicates. Serialize to `manifest.json`.
2. `IntelligenceHandler()`: Pipe prompts with `manifest.json` against LLM. Output detailed classification array detailing `Agent` targeting matrices.
3. `AgentOrchestrator()`: Read LLM response mappings. Instantiate multiple independent asynchronous software Agents mapped specifically to platform bindings.
4. `TaskExecutorAsync()`: Agents execute toolsets (`gdown`, `yt-dlp`) asynchronously with buffered read-streams routing into localized hardware caches. Telemetry binds out to tracking `.jsonl`.
5. `AssetArchiver()`: Files transition from staging vectors into structured Cloud integrations mapping `Root/Platform/Campaign/Name.mp4`.
6. `ReporterView()`: System aggregates log streams generating unified UI `.html` output displaying successfully mitigated task footprints and unhandled failures.

---

## 9. IMPLEMENTATION PLAN

*This plan represents a linear milestone delivery mapping the construction of the overall Retrieval platform.*

- **Phase 1: Extraction & Preprocessing Engine** 
  Develop the input layer via `pandas/openpyxl`. Configure chunk-based file ingest capabilities spanning scaling arrays up to 1M rows. Implement regex detection bindings and initial JSON schema serialization.
  
- **Phase 2: Classification System Inference Integrations** 
  Build bridging architectures to LLM models. Devise efficient prompt templates matching URLs to categorical matrices and integrating rule-based overrides for standard edge cases.

- **Phase 3: Agent Orchestration Engine**
  Construct the asynchronous agent deployment factory. Set rules strictly segregating agents to map to assigned platform methodologies. Ensure agents accept parameter structures matching Phase 2 implementations.

- **Phase 4: Execution Toolkit & Telemetry Monitoring** 
  Integrate the execution layer scripts natively invoking utilities like `yt-dlp` and `gdown`. Code standard standard-out parsers funneling tool activity into a central telemetry stream exporting `.jsonl` and Google Sheets logs comprehensively defining heartbeat states.

- **Phase 5: Cloud Organization & Document Reporting**
  Finalize Cloud Drive API integrations mirroring intelligent classifications. Link tagging heuristic metadata for dynamic file naming modifications. Program final `.xlsx` discrepancy and aggregated structured `.html` summary output generation.
