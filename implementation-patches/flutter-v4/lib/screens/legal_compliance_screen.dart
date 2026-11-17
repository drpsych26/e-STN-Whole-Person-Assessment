import "package:flutter/material.dart";

class LegalComplianceScreen extends StatelessWidget {
  const LegalComplianceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Legal & Compliance")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          _Section(
            title: "Supportive Therapy Network Limited",
            body: "Copyright (c) 2026 Supportive Therapy Network Limited. All rights reserved. STN-owned source code, documentation, designs, assessment workflows and materials are proprietary except for third-party components governed by their own licence terms. No permission is granted to use, copy, modify, distribute, sublicense, publish, deploy or commercially exploit STN-owned materials without prior written permission.",
          ),
          _Section(
            title: "Clinical certifications and approvals",
            body: "STN maintains a controlled register of applicable organisational, service, facility and practitioner certifications and approvals. Certificate references, issuing authorities, scopes, issue dates and expiry or review dates must be entered from current source documents and verified before publication. This screen does not itself constitute evidence of certification or regulatory approval.",
          ),
          _Section(
            title: "Professional credentials",
            body: "Clinical services must be delivered by practitioners who hold the registration, practising authority and scope required for their profession and role. Practitioner-specific credentials must be verified against the relevant official register and must not be inferred from STN's organisational status.",
          ),
          _Section(
            title: "Assessment instruments and third-party licences",
            body: "Each assessment instrument, questionnaire, scoring method, translation, font, software package and third-party component remains subject to its own copyright and licence terms. Electronic reproduction, scoring, adaptation, commercial use and distribution require permissions covering the actual use. STN's proprietary notice does not override third-party licences.",
          ),
          _Section(
            title: "Privacy and health information",
            body: "Personal and health information must be handled under applicable New Zealand privacy and health-information requirements. The production service must provide approved privacy information, consent and lawful-authority workflows, access and correction processes, retention and disposal controls, and appropriate security safeguards. Do not enter real client information into this development build.",
          ),
          _Section(
            title: "Consumer rights and clinical governance",
            body: "Applicable consumer rights, informed consent, effective communication, reasonable care and skill, complaints handling and safety obligations must be met. Clinical decisions remain the responsibility of an appropriately authorised practitioner. Software outputs are decision support and must not independently diagnose, clear risk or replace professional judgement.",
          ),
          _Section(
            title: "Security and intended use",
            body: "This application build is a development and controlled-testing build. It is not authorised by this notice for processing identifiable client health information. Production use requires approved hosting, authenticated clinician access, role-based permissions, persistent managed records, audit trails, encryption, tested backups and recovery, incident response, security testing and signed clinical and operational release approval.",
          ),
          _Section(
            title: "Evidence register status",
            body: "Certificate numbers, licence references, registration details and approval dates are not populated in this build because the underlying evidence has not been attached to this release for verification. Insert only accurate, current details from source documents. Do not publish invented or generic certificate identifiers.",
          ),
          Padding(
            padding: EdgeInsets.only(top: 8, bottom: 24),
            child: Text(
              "Document revision 1.0 • 18 November 2026 • Supportive Therapy Network Limited",
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final String body;

  const _Section({required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(body),
          ],
        ),
      ),
    );
  }
}
