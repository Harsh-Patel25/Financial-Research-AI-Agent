

# 🟡 PHASE 2 – RAG & ADVANCED FEATURES

---

# 🔹 TASK 7 – Document Ingestion

---

## 📄 Implement PDF Loader

```
Implement a PDF document loader.

Requirements:
1. Use PyPDF or LangChain PDFLoader.
2. Extract raw text from each page.
3. Preserve page number metadata.
4. Return structured document object (content + metadata).
5. Handle corrupted PDF gracefully.

Do not implement embedding yet.
Keep ingestion logic separate from API routes.
```

---

## ✂ Implement Text Extraction & Cleaning

```
Implement text preprocessing for extracted PDF content.

Requirements:
1. Remove excessive whitespace.
2. Normalize line breaks.
3. Remove non-printable characters.
4. Keep financial numbers intact.
5. Ensure no data loss.

Make this a separate utility function.
```

---

## 🔪 Apply RecursiveCharacterTextSplitter

```
Integrate RecursiveCharacterTextSplitter.

Requirements:
1. Set chunk size (e.g., 800-1000 chars).
2. Set overlap (e.g., 100-200 chars).
3. Preserve metadata per chunk.
4. Return list of structured chunk objects.
5. Log total chunks created.

Keep chunking logic modular.
```

---

## 🏷 Store Metadata

```
Attach metadata to each chunk.

Include:
- source file name
- page number
- document date (if available)
- ingestion timestamp

Ensure metadata is included when storing in vector DB.
```

---

# 🔹 TASK 7.5 – Vector DB Persistence (Chroma)

---

## 💾 Setup Persistent Chroma

```
Initialize Chroma vector database in persistent mode.

Requirements:
1. Store DB on disk (not memory).
2. Define collection name.
3. Ensure data persists after restart.
4. Validate collection existence before creating new one.
5. Log DB initialization status.
```

---

## 🔄 Implement Collection Versioning

```
Implement simple versioning for vector collections.

Requirements:
1. Add version identifier in metadata.
2. Allow re-indexing without data corruption.
3. Prevent duplicate indexing.
```

---

## ⚡ Add Metadata Indexing

```
Ensure Chroma stores metadata properly.

Requirements:
1. Enable filtering by metadata fields.
2. Test filtering functionality.
3. Log sample retrieval with metadata.
```

---

# 🔹 TASK 8 – Embeddings Pipeline

---

## 🧠 Generate Embeddings

```
Implement embedding generation.

Requirements:
1. Use OpenAI text-embedding-3-small OR HuggingFace model.
2. Generate embeddings per chunk.
3. Batch embeddings for efficiency.
4. Handle API failures gracefully.
5. Log embedding latency.
```

---

## 💾 Store Embeddings in Chroma

```
Store generated embeddings in Chroma.

Requirements:
1. Store chunk content + metadata.
2. Ensure idempotency (no duplicates).
3. Validate vector count.
4. Log total stored vectors.
```

---

## 🔁 Implement Embedding Version Control

```
Add embedding model version tracking.

Requirements:
1. Store embedding model name in metadata.
2. Detect mismatch between stored and current embedding model.
3. Trigger re-embedding warning if mismatch.
```

---

# 🔹 TASK 9 – Semantic Retrieval

---

## 🔎 Convert Query to Embedding

```
Implement query embedding generation.

Requirements:
1. Convert user query into embedding vector.
2. Use same embedding model as stored data.
3. Log embedding generation time.
```

---

## 🔍 Perform Similarity Search

```
Implement similarity search in Chroma.

Requirements:
1. Retrieve top-k results (e.g., k=5).
2. Include similarity score.
3. Log retrieved documents.
4. Handle empty result safely.
```

---

## 🎯 Apply Score Threshold Filtering

```
Filter similarity search results.

Requirements:
1. Exclude results below threshold score.
2. Define threshold configurable via settings.
3. Log discarded chunks.
```

---

## 🧩 Inject Retrieved Context into LLM Prompt

```
Integrate retrieved chunks into LLM prompt.

Requirements:
1. Inject as contextual block.
2. Maintain clean formatting.
3. Avoid exceeding token limit.
4. Log context length.
```

---

## 📊 Add Retrieval Logging

```
Log retrieval diagnostics.

Requirements:
1. Log query text.
2. Log retrieved chunk IDs.
3. Log similarity scores.
4. Enable debugging mode for inspection.
```

---

# 🔴 PHASE 3 – PRODUCTION READINESS

---

# 🔹 TASK 10 – Evaluation & Observability

---

## 📝 Create Gold Evaluation Dataset

```
Create evaluation dataset file.

Requirements:
1. Include question.
2. Include expected structured answer.
3. Store in JSON or YAML.
4. Ensure version control.
```

---

## 📊 Expand Test Query Dataset

```
Add 50+ diverse financial queries.

Cover:
- Stock analysis
- News queries
- Portfolio queries
- Edge cases

Ensure test coverage.
```

---

## ⚖ Implement Evaluation Script

```
Create evaluation script.

Requirements:
1. Run test queries through system.
2. Compare output against gold dataset.
3. Score accuracy.
4. Log failures.
```

---

## 🔍 Integrate LLM Tracing

```
Integrate LLM tracing tool (LangSmith or structured logs).

Requirements:
1. Log prompt.
2. Log response.
3. Log token usage.
4. Log latency.
```

---

## 📈 Add Performance Metrics

```
Implement performance tracking.

Track:
- Latency per request
- Token usage
- API cost estimate
- Error rate

Expose metrics via logs or /metrics endpoint.
```

---

# 🔹 TASK 11 – Caching & Rate Limiting

---

## 🧠 Integrate Redis Caching

```
Integrate Redis as caching backend.

Requirements:
1. Cache stock responses (TTL 1-5 min).
2. Cache news responses (TTL 30-60 min).
3. Optional cache embeddings.
4. Log cache hits/misses.
```

---

## 🚦 Implement API Rate Limiting

```
Integrate slowapi for rate limiting.

Requirements:
1. Apply per-IP rate limits.
2. Return HTTP 429 for exceeded limits.
3. Log rate limit violations.
```

---

## 👤 Add Per-User Limits

```
Extend rate limiting to per-user logic.

Requirements:
1. Identify user via API key or token.
2. Apply stricter limits if needed.
3. Log abuse attempts.
```

---

# 🔹 TASK 12 – Deployment & CI/CD

---

## 🐳 Finalize Dockerfile (Multi-stage)

```
Refactor Dockerfile to multi-stage build.

Requirements:
1. Separate build and runtime layers.
2. Minimize image size.
3. Expose correct port.
4. Test container locally.
```

---

## 🐳 Finalize docker-compose

```
Finalize docker-compose.yml.

Services:
- App
- PostgreSQL
- Redis

Ensure environment variables passed correctly.
```

---

## 🔁 Setup GitHub Actions

```
Create GitHub Actions workflow.

Steps:
1. Install dependencies.
2. Run lint.
3. Run pytest.
4. Build Docker image.
Fail pipeline if any step fails.
```

---

## 🌍 Environment Configuration

```
Implement environment-based configuration.

Requirements:
1. Dev / Staging / Prod config separation.
2. Provide .env.example.
3. Validate environment on startup.
```

---

# 🔥 Ab Tumhara Plan Full Professional Ho Chuka Hai

Ab tumhara roadmap:

* Deterministic core
* Controlled RAG
* Observability
* Evaluation
* Deployment ready

Yeh student project nahi raha.
Yeh production-grade system roadmap hai.

