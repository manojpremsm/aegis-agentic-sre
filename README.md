# Aegis — Multi-Agent AI SRE Incident Investigator

## Overview

Aegis is a distributed, multi-agent AI system designed to automate incident investigations in microservices environments.

Its architecture separates incident simulation, investigation processing, and shared event contracts into independently defined components. The planned system will use asynchronous communication and durable workflow execution to investigate incidents reliably.

Aegis will analyze incident alerts, logs, metrics, and deployment changes to identify likely root causes and generate evidence-backed investigation reports for human review.

The initial version will operate against a controlled microservices incident simulator, with external monitoring integrations considered for future development.

## Problem Statement

Investigating incidents in distributed systems is challenging because relevant evidence is often scattered across multiple services, logs, monitoring systems, and deployment records.

Site Reliability Engineers (SREs) must correlate this information to determine what failed, when it failed, and which changes may have caused the failure. This process can be time-consuming, especially when multiple services are affected.

Aegis aims to reduce investigation time by automatically collecting and correlating available evidence, identifying likely root causes, and producing structured reports for human review.

Aegis is designed as a read-only investigation assistant and will not autonomously execute remediation actions.

## Architecture

Aegis is organized as a monorepo containing three independently installable Python packages.

| Component | Responsibility |
|---|---|
| `apps/simulator` | Simulates microservices incidents and generates incident events and telemetry. |
| `apps/investigator` | Receives incident events and will coordinate evidence collection, investigation workflows, and report generation. |
| `packages/contracts` | Defines shared data contracts used for communication between the applications. |

The simulator and investigator are designed as independently deployable applications. They share data contracts but do not directly depend on each other's implementation.

The planned architecture uses asynchronous messaging to decouple incident generation from investigation processing. Durable workflow state, idempotent event handling, and retry mechanisms will support reliable incident processing.

**Current implementation status:** The repository structure and Python packaging are initialized. Incident simulation, messaging, investigation workflows, and AI agents are not yet implemented.
