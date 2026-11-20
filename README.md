# Intelligent Academic Assistant for Document-Based Question Answering

A locally hosted Retrieval-Augmented Generation (RAG) application that
lets users upload academic PDF documents and ask questions grounded in
their contents. The application extracts text, splits it into chunks,
creates embeddings, indexes the chunks in FAISS, retrieves relevant
passages, and generates answers using a locally running Ollama language
model.

> **Project status:** This README documents the intended
> local-development setup based on the project architecture. Verify the
> actual backend entry point, package versions, and configured ports in
> your repository before final submission.

## 1. Project objectives

-   Upload an academic PDF and process its contents.
-   Extract text page by page, with OCR fallback for scanned pages.
-   Split extracted text into overlapping chunks while preserving page
    references.
-   Generate embeddings locally using Ollama.
-   Store and search document vectors with FAISS.
-   Retrieve relevant passages for a user's question.
-   Generate grounded answers with source/page references.
-   Avoid sending document content to paid or external AI APIs.

## 2. Technology stack

  -----------------------------------------------------------------------
  Layer                               Technology
  ----------------------------------- -----------------------------------
  Frontend                            Angular 15, TypeScript, Angular
                                      Material (if enabled in the UI)

  Backend                             Python, FastAPI

  PDF extraction                      PyMuPDF (`fitz`), pypdf

  OCR fallback                        Tesseract OCR, Pillow

  Embeddings                          Ollama `nomic-embed-text`

  Answer generation                   Ollama `llama3.2:3b`

  Vector search                       FAISS, NumPy

  HTTP client                         httpx

  Local model runtime                 Ollama
  -----------------------------------------------------------------------

The application uses RAG rather than fine-tuning the language model. The
model is prompted with retrieved document passages at question time.

## 3. High-level workflow

1.  The user selects and uploads a PDF.
2.  The FastAPI backend validates the file and extracts text page by
    page.
3.  OCR is attempted for pages whose extracted text is below the
    configured minimum.
4.  Text is split into chunks (currently documented defaults: 1,000
    characters with 150-character overlap).
5.  The backend generates embeddings using `nomic-embed-text`.
6.  Normalized vectors are stored in a FAISS inner-product index.
7.  When a question is submitted, the same embedding model vectorizes
    the question.
8.  FAISS retrieves the most relevant chunks for that document.
9.  The answer service uses retrieved context and `llama3.2:3b` to
    produce a grounded response.
10. The UI displays the answer and its source references.

Each question must be scoped to the selected document ID. Do not combine
chunks or indexes from different uploaded PDFs.

## 4. Prerequisites

Install the following on macOS:

-   Git
-   Python 3.9 or a Python version supported by the packages pinned in
    the project
-   Node.js and npm compatible with the Angular CLI version in the
    repository
-   Ollama
-   Tesseract OCR
-   Docker only if your local backend configuration requires PostgreSQL
    or another containerized dependency

Check installed versions:

``` bash
python3 --version
node --version
npm --version
ollama --version
```

Install Tesseract with Homebrew:

``` bash
brew install tesseract
tesseract --version
```

Install Ollama from its official installer, then start the Ollama
application/service.

## 5. Download local models

Pull the models used by the application:

``` bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Confirm that they are available:

``` bash
ollama list
```

Ensure Ollama is running and responds locally:

``` bash
curl http://localhost:11434/api/tags
```

The embedding model used to create the document index must remain the
same model used to embed questions. If you change the embedding model,
rebuild all document indexes.

## 6. Backend setup

Change to the backend directory. Adjust the path to match your
repository:

``` bash
cd <PROJECT_ROOT>/backend
```

Create and activate a virtual environment:

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade packaging tools:

``` bash
python -m pip install --upgrade pip setuptools wheel
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

If the repository does not yet contain a `requirements.txt`, create one
from the project's actual imports and tested versions. Do not use an
unpinned, guessed dependency list for the final reproducibility
submission.

### Environment variables

Create a `.env` file in the location read by your backend settings
module. Example:

``` dotenv
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
EMBEDDING_MODEL=nomic-embed-text
RAG_MIN_SIMILARITY_SCORE=0.30
```

These names must match the environment-variable names actually read by
your code. Keep secrets out of source control. The local Ollama setup
described here does not require a paid API key.

### Start the backend

Use the entry point and ASGI import path defined by your repository. For
example, if the FastAPI instance is `app` in `app.main`:

``` bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

If your application uses a different module path or port, substitute the
actual values. Check the API documentation after startup:

``` text
http://127.0.0.1:8001/docs
```

The Angular service in the current project notes was configured with:

``` text
http://127.0.0.1:8001/api/documents
```

Confirm that this matches the backend port and router prefix before
running the frontend.

## 7. Frontend setup

Open a second terminal and change to the Angular application directory:

``` bash
cd <PROJECT_ROOT>/frontend
```

Install dependencies:

``` bash
npm install
```

Start the Angular development server:

``` bash
npx ng serve --host 127.0.0.1 --port 4200
```

Open:

``` text
http://127.0.0.1:4200
```

If your Angular project is located in a different directory, run these
commands from the directory containing `package.json` and
`angular.json`.

## 8. Using the application

1.  Start Ollama.
2.  Start the FastAPI backend.
3.  Start the Angular frontend.
4.  Open the frontend in a browser.
5.  Upload a PDF within the configured 10 MB limit.
6.  Wait for extraction and indexing to finish.
7.  Confirm the displayed page and chunk counts.
8.  Ask a question whose answer is present in the uploaded PDF.
9.  Review the answer and its source/page references.
10. Upload a different PDF and verify that questions are answered only
    from the newly selected document.

A useful grounding test is to ask a question whose answer is clearly
present, followed by a question whose answer is absent. The second
question should return a clear not-found response rather than inventing
an answer.

## 9. API overview

The current router design uses the prefix `/api/documents`.

  ---------------------------------------------------------------------------------------
  Method                  Endpoint                                Purpose
  ----------------------- --------------------------------------- -----------------------
  POST                    `/api/documents/upload`                 Upload, process, and
                                                                  index a PDF

  POST                    `/api/documents/{document_id}/index`    Build or rebuild a
                                                                  document index

  POST                    `/api/documents/{document_id}/search`   Retrieve relevant
                                                                  chunks

  POST                    `/api/documents/{document_id}/ask`      Ask a question against
                                                                  one document
  ---------------------------------------------------------------------------------------

Use the interactive FastAPI `/docs` page to confirm request and response
schemas for the implemented version.

## 10. Configuration and implementation notes

-   **Chunking:** The documented defaults are 1,000 characters per chunk
    and 150 characters of overlap. Confirm the values in the current
    source before reporting them as final.
-   **OCR:** Pages with fewer than 40 extracted characters are
    candidates for OCR in the described implementation. Truly blank
    pages will remain blank.
-   **Vector similarity:** The described FAISS implementation normalizes
    vectors and uses `IndexFlatIP`, making inner product equivalent to
    cosine similarity for normalized vectors.
-   **Retrieval threshold:** The documented starting threshold is
    `0.30`. Tune it only after evaluating representative questions.
-   **Top-k:** The frontend should use the same configured retrieval
    behavior as the backend. The current implementation notes mention a
    top-k value of 5 for question answering.
-   **Model training:** No fine-tuning is claimed. The solution uses a
    pretrained local model, local embeddings, retrieval, and
    prompt-based generation.
-   **Document isolation:** Every ask/search request must include the
    active document ID. Never reuse a previous document's index after a
    new upload.

## 11. Evaluation checklist

Run and record tests against the final version. Include the exact PDF,
question, expected answer, actual answer, source page, and pass/fail
result.

  -----------------------------------------------------------------------
  Test                                Expected behavior
  ----------------------------------- -----------------------------------
  Fact present on a page              Correct answer with supporting
                                      source/page

  Fact absent from PDF                Explicit not-found response

  Different PDF selected              No answer leakage from the previous
                                      PDF

  Multi-chunk answer                  Relevant passages retrieved from
                                      the same document

  Blank PDF page                      No fabricated text or OCR result

  Invalid file type                   Upload rejected

  PDF above size limit                Upload rejected

  Ollama unavailable                  Clear backend error; no fabricated
                                      answer
  -----------------------------------------------------------------------

Do not report an accuracy percentage until the test set, ground truth,
and results have been rerun and recorded for the final build.

## 12. Troubleshooting

### Ollama connection error

-   Confirm the Ollama application/service is running.
-   Run `ollama list`.
-   Test `curl http://localhost:11434/api/tags`.
-   Confirm `OLLAMA_URL` is correct.

### Model not found

``` bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama list
```

### Embedding dimension mismatch

Use the same embedding model for indexing and querying. After changing
the embedding model, delete/rebuild the affected FAISS indexes using the
application's supported re-index operation.

### PDF text is missing

-   Check whether the PDF contains selectable text.
-   Confirm Tesseract is installed and available on `PATH`.
-   Inspect the extracted page text and OCR output.
-   Remember that blank pages do not contain recoverable text.

### Frontend cannot reach the backend

-   Confirm FastAPI is running.
-   Confirm the Angular API base URL and backend port match.
-   Check CORS configuration.
-   Inspect browser developer tools and FastAPI logs.

### Port already in use

Stop the process using the port or select another port, then update the
frontend API URL to match.

## 13. Storage and generated files

The described backend stores uploaded documents, processed text/chunk
metadata, and FAISS indexes under backend storage directories,
typically:

``` text
backend/
└── storage/
    ├── documents/
    ├── processed/
    └── indexes/
```

Confirm the actual paths in `pdf_service.py` and `vector_store.py`.
These directories may contain uploaded academic documents and derived
data; do not commit private or sensitive PDFs to a public repository.

## 14. Suggested repository structure

The following is an illustrative structure. Keep the actual repository
layout as the source of truth.

``` text
academic-assistant/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   └── main.py
│   ├── storage/
│   │   ├── documents/
│   │   ├── processed/
│   │   └── indexes/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── angular.json
├── README.md
└── .gitignore
```

## 15. Security and privacy

-   Keep `.env`, credentials, and private documents out of Git.
-   Validate file extension, content signature, and maximum upload size
    on the backend.
-   Treat uploaded PDF content as untrusted input.
-   Keep answers grounded in retrieved passages and show source
    references.
-   Run locally unless a separately reviewed deployment configuration is
    introduced.
-   Do not claim production-grade authentication, authorization,
    encryption, or cloud deployment unless those controls are
    implemented and tested.

## 16. Limitations and future enhancements

Current limitations to document honestly:

-   Retrieval quality depends on PDF extraction, chunking, embedding
    quality, and threshold selection.
-   Complex tables, diagrams, handwriting, and low-quality scans may not
    be extracted reliably.
-   A small local language model may produce incomplete answers or
    require additional latency.
-   OCR quality depends on scan quality and installed language data.
-   The system has not been fine-tuned unless a separate training
    workflow is added and evidenced.

Potential future enhancements:

-   Better table and layout extraction.
-   Support for multiple OCR languages.
-   Hybrid keyword and vector retrieval with reranking.
-   Conversation history scoped to a document.
-   Automated evaluation with a curated question/answer dataset.
-   User authentication and document-level access controls.
-   Containerized, reproducible deployment.

## 17. Academic project deliverables

For the capstone submission, prepare these three items:

1.  **Presentation slides** covering the problem statement, approach,
    solution steps, architecture, results, limitations, and future work.
2.  **Project report** with enough technical detail for another person
    to reproduce the setup and methodology.
3.  **Demonstration video** of no more than 10 minutes, using the slides
    and demonstrating every feature or result claimed.

The source code does not need to be submitted under the stated faculty
instructions. Keep a working repository available for your own
demonstration and verification.

## 18. Final pre-submission checklist

-   [ ] Fresh setup tested from the README on the target Mac.
-   [ ] Python and Node versions recorded.
-   [ ] Dependency versions pinned in project files.
-   [ ] Ollama models and model names verified.
-   [ ] Backend entry point and port verified.
-   [ ] Frontend API URL verified.
-   [ ] Upload, extraction, chunking, indexing, retrieval, and answer
    generation tested.
-   [ ] Document isolation tested with at least two different PDFs.
-   [ ] Evaluation prompts, expected answers, outputs, and evidence
    recorded.
-   [ ] Screenshots and demo recording match the final build.
-   [ ] No unsupported performance or accuracy claims in the report or
    slides.
-   [ ] `.env`, private PDFs, and generated indexes excluded from public
    Git if appropriate.
