# Enterprise Security Knowledge & Ticket Resolution Agent

A planned read-only assistant for evidence-grounded Privileged Access Management (PAM) knowledge Q&A and synthetic support-ticket investigation. Built as a capstone for Alexey Grigorev's AI Engineering Buildcamp: From RAG to Agents.

## The Problem

Enterprise security engineers and PAM support teams often need to investigate issues using scattered documentation, asset details, and past support cases. Finding reliable evidence is especially difficult for engineers who are new to an environment.

## Planned Workflows

- **Knowledge Q&A:** Ask a PAM question and receive an answer grounded in documentation, with source citations and explicit gaps where evidence is missing.
- **Ticket investigation:** Provide a synthetic support ticket and receive an issue category, relevant findings, suggested checks, citations, missing information, uncertainties, and escalation advice when evidence is insufficient.

The initial MVP will cover **account onboarding, password rotation, and custom web connector troubleshooting**. One tool-calling agent will use three read-only tools: `search_documentation(query)`, `get_asset_details(asset_id)`, and `search_past_tickets(query)`.

For example, a ticket might ask: "Password rotation failed for a Linux privileged account on LNX-001 shortly after onboarding. What should I check?"

## Current Status

The repository currently contains the course starter's setup smoke-test notebook and a minimal RAG (retrieval-augmented generation) notebook using example data. The security workflows, tools, project-specific retrieval, and evaluation are planned and have not yet been implemented. The starter notebooks have not yet been verified for this project.

The MVP will use only permitted public documentation and synthetic asset records and tickets. It will not access real customer data or credentials, connect to live vendor systems, or change accounts or passwords.

## Setup

1. Install uv if you don't have it yet: https://docs.astral.sh/uv/getting-started/installation/

2. Clone this repository (or download the zip and extract it).

3. Create a `.env` file from the template and add your API key:

       cp .env.example .env

4. Install dependencies:

       uv sync

5. Start Jupyter:

       uv run jupyter notebook

## Notebooks

- `notebooks/01-setup.ipynb` - smoke test that confirms your environment works
- `notebooks/02-rag.ipynb` - a minimal RAG baseline you can adapt to your own data

## Data

The `data/` folder is currently empty. Planned project data will include permitted public documentation and synthetic asset records and support tickets. See `notebooks/02-rag.ipynb` for the starter's data-loading example.
