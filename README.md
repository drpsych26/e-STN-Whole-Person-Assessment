# STN Whole Person Assessment — Digital Prototype

This private repository is the home for the Supportive Therapy Network (STN) Whole Person Initial Assessment digital prototype and its supporting technical pack.

## Intended workflow

Dashboard → New Client → Whole Person Initial Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Whole-Person Care Plan → Finalise → Report.

## Prototype status

The browser prototype is a development demonstration, not a production-ready or clinically validated diagnostic system. Prototype questions and scores must not be represented as validated instruments or used alone to diagnose, triage, or make treatment decisions. A qualified clinician must determine risk disposition, diagnosis, and treatment.

Before real-client use, implement authentication, role-based access, encryption, server-side audit trails, backups, privacy notices, consent, retention/deletion controls, and security testing. Replace demonstration content with approved/licensed instruments and governed scoring rules, and validate safety escalation and adaptive routing with qualified clinicians.

## Privacy

Keep this repository private. Do not commit real client information, credentials, API keys, private keys, production database exports, or identifiable clinical records. A private GitHub repository is still hosted by GitHub and is not offline-only storage.

## Planned structure

- `prototype/` — tablet-friendly browser workflow
- `flutter/` — supplied Flutter MVP/coding packs
- `reference/` — paper assessment, specifications, and New Zealand production requirements

## Current import note

The repository is being populated from the approved STN Digital Prototype GitHub Pack. The full reference pack and Flutter archives must be transferred and checked before this repository is considered a complete project import.