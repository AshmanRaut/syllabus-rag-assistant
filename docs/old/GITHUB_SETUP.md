# Publish this starter scaffold to your GitHub account

This ZIP is a local starter repository scaffold; it has not been pushed to a remote GitHub account. Create an empty GitHub repository named `syllabus-rag-assistant` in your browser (do not initialise it with a README or license), then run these commands from the extracted folder:

```bash
git init -b main
git add .
git status --short
git commit -m "chore: initial syllabus RAG assistant scaffold"
git remote add origin https://github.com/YOUR_USERNAME/syllabus-rag-assistant.git
git push -u origin main
```

Before pushing, check that `.env`, original course notes, OCR cache, generated page images, `chunks.jsonl`, and Qdrant data are not staged. `.gitignore` excludes these by default. Do not commit API keys or private course material.

Create four branches after the base contract commit:

```bash
git switch -c feat/ingestion-ocr
# Person A works here; push branch and open PR

git switch main
git pull
git switch -c feat/qdrant-hybrid-web
# Person B works here
```

Repeat for `feat/generation-citations` (Person C) and `feat/ui-evaluation` (Person D). Keep each owner in the paths listed in `GIT_WORKFLOW.md`.
