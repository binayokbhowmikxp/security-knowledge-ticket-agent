# Enterprise Security Knowledge & Ticket Resolution Agent

A planned read-only assistant for evidence-grounded Privileged Access Management (PAM) knowledge Q&A and synthetic support-ticket investigation. Built as a capstone for Alexey Grigorev's AI Engineering Buildcamp: From RAG to Agents.

## The Problem

Modern organizations rely on hundreds or thousands of servers, databases, applications, and cloud services to run their business. Many of these systems use privileged accounts — accounts with elevated permissions that can perform sensitive operations, such as administering servers, managing databases, or accessing critical infrastructure.

Privileged Access Management (PAM) solutions, such as CyberArk, help organizations secure and manage these powerful accounts. They provide capabilities such as credential management, password rotation, privileged session monitoring, and controlled access to critical systems.

However, managing and troubleshooting a PAM environment can be challenging.

### The Knowledge Problem

In a large enterprise, technical knowledge is often scattered across multiple sources:

- Vendor documentation: Product configurations, integration guides, troubleshooting procedures, and best practices.
- Internal knowledge bases: Organization-specific instructions, security policies, and onboarding procedures.
- Environment information: Details about servers, applications, databases, privileged accounts, and their configurations.
- Historical support tickets: Previously encountered issues, investigations, and resolutions.
- Custom integrations: Documentation for application-specific connectors and configurations.

Although this information may already exist, finding the right information at the right time is often difficult.

Experienced engineers may know exactly where to look, while newer engineers may spend hours or even days searching documentation, consulting colleagues, and investigating issues.

### A Real-World Example

Imagine a security engineer receives the following support ticket:

> "The automated password rotation for a privileged account on a Linux server has failed. Please investigate."

Before recommending a solution, the engineer may need to:

1. Identify the affected server and privileged account.
2. Understand how the account is configured in the PAM system.
3. Locate the relevant vendor troubleshooting documentation.
4. Search for similar incidents and their previous resolutions.
5. Identify possible causes and determine appropriate troubleshooting steps.

Completing this investigation can require searching multiple systems and manually connecting information from different sources.

### Why This Matters

Inefficient knowledge discovery and troubleshooting can lead to:

- Longer incident investigation and resolution times.
- Increased dependency on experienced engineers.
- Repeated investigations of previously encountered problems.
- Inconsistent troubleshooting approaches.
- Delays in supporting business-critical systems.

This project aims to reduce the time engineers spend searching for information and investigating common PAM issues.

It will explore how Retrieval-Augmented Generation (RAG) and tool-calling AI agents can bring relevant knowledge together, investigate support tickets, and provide evidence-backed troubleshooting guidance.

The system is intended to assist engineers, not replace their judgment or automatically modify critical infrastructure.

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
