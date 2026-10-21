# STN production NZ requirements

This is an engineering/governance checklist, not legal advice. Confirm applicable law and current guidance with qualified New Zealand privacy and clinical governance advisers before production.

## Health information privacy
STN's production service will handle identifiable health information. Assess the Health Information Privacy Code 2020 as currently in force and any amendments, alongside applicable privacy legislation and professional obligations.

Engineering implications:
- collect only information needed for the stated purpose;
- provide clear notice about collection, use and disclosure;
- apply reasonable security safeguards;
- support access and correction workflows;
- control disclosures and overseas processing;
- implement retention/disposal rules;
- maintain a documented privacy/security risk assessment.

## Consumer rights
Design services to meet applicable Health and Disability Commissioner consumer-rights requirements, including privacy, reasonable care and skill, effective communication, relevant information, and informed consent.

## Clinical governance
Before production:
- approve the STN Clinical Core release;
- verify each instrument's licence/permission and exact scoring/version;
- define clinician roles and accountability;
- validate diagnostic decision-support logic;
- define crisis escalation and human response;
- establish change control and regression testing;
- complete UAT and security testing.

## Data architecture
Do not use browser localStorage as the clinical record. The browser prototype is a demonstration until authenticated persistence and audit controls are deployed.
