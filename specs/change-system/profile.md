project: autolinkedinpost
stack:
  languages:
    - python
  frameworks:
    - playwright
    - google-genai
    - pymupdf
    - pillow
  runtime:
    - python 3.11+
architecture:
  app_type: automation-bot
  main_areas:
    - src
    - tests
    - bot.py
    - main.py
conventions:
  branching: trunk-based
  testing_style: tdd
  spec_style: delta
testing:
  unit: python -m pytest
  integration: null
  e2e: null
  default_command: python -m pytest
quality:
  lint_command: null
  typecheck_command: null
notes:
  - Automated LinkedIn post generator with PDF carousel rendering via Playwright
updated_at: '2026-09-03T11:20:00+00:00'

