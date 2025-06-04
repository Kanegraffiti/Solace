#!/bin/bash
pip install --quiet nltk markdown docutils pdfplumber ebooklib beautifulsoup4
python - <<'PY'
import nltk
nltk.download('punkt')
PY
