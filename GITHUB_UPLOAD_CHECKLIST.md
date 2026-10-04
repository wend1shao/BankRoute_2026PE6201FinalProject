# GitHub upload checklist

This folder is the clean repository root.

## Included

- Python source code and Flask API/demo
- Polished English frontend source
- `requirements.txt` and frontend lockfile
- BANKING77 source data plus data explanation and hashes
- Trained artefacts and thresholds required to run without retraining
- Frozen evaluation inputs, results, and explanation
- Automated tests
- Architecture, product, and demo documentation
- Run instructions and verified metrics
- Project and dataset licence information

## Intentionally excluded

- Virtual environments, `node_modules`, build outputs, caches, and `__pycache__`
- Local audit logs and editor logs
- PowerPoint, speaker notes, report files, and course-preparation material
- `.git` history from local working copies
- Hosting metadata and local deployment state
- API keys, `.env` files, and customer data

## Before pushing

```bash
git init
git add .
git status
git commit -m "Add BankRoute final project"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Review `git status` before committing. Do not add a real `.env` file or secret.
