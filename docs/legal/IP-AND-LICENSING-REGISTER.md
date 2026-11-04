# STN intellectual property and licensing register

**Status:** Controlled working register — evidence is required before an entry can be marked verified.  
**Owner:** Supportive Therapy Network Limited  
**Last reviewed:** 4 November 2026  
**Review trigger:** Each material source, contributor, dependency, instrument, asset or release change.

This register distinguishes the intended STN ownership position from legally evidenced ownership and third-party permissions. A copyright notice is not an assignment. A repository being private does not establish title. Do not describe any item as fully cleared unless the evidence below has been checked and retained.

## Asset and rights register

| Asset / component | Intended or identified rights holder | Evidence required | Current status |
|---|---|---|---|
| STN original application code | STN only to the extent created by employees/contractors under effective terms or assigned in writing | Contributor history, employment/contract IP clauses, signed assignments, provenance | **Not verified — evidence required** |
| STN name and brand identity | STN / original creator as established by provenance and assignment | Original design files, creator identity, dated source, assignment/licence, NZ and relevant-market trademark search | **Not verified — evidence required** |
| STN brain/head logo and wordmark | STN only if creator rights are owned or assigned | Original source file, creator, creation date, signed assignment, any third-party source elements, trademark search | **Not verified — evidence required** |
| Website and assessment UI designs | STN / named designers and contributors | Source provenance, contributor agreements, assignment or licence, asset inventory | **Not verified — evidence required** |
| Assessment item wording / paper pilot | Original author or instrument rights holder; STN only for original wording it owns | Item-level source map, authorship, licence, written digital display/reproduction/storage/export/translation permissions | **Not verified — item-level evidence required** |
| PHQ-9, GAD-7 or other named third-party measures | Relevant instrument owner / licensor | Exact version, official terms, written permissions where required, permitted populations, translations, digital use, scoring and reporting | **Not cleared — do not embed/use beyond confirmed permission** |
| STN scoring rules and clinical algorithms | Original author / STN only to extent owned; clinical validity is a separate issue | Authorship, source, review history, validation evidence, approval and permission record | **Not verified** |
| Flutter and Dart SDK | Google / Flutter and Dart project | SDK version, upstream licence texts and notices | **Third-party — preserve upstream terms** |
| Dart / Flutter packages | Respective package maintainers | Lockfile, exact version, transitive dependency inventory, SPDX identifiers, licence texts, vulnerability report | **Per-build scan required** |
| JavaScript / web dependencies | Respective package maintainers | Exact version and source, dependency lock data, SPDX identifier, licence text and notices | **Inventory and scan required** |
| Fonts, icons, images and templates | Respective creators / licensors | Exact asset, source URL, licence, attribution, commercial-use and redistribution permissions | **Asset-level evidence required** |
| External APIs, hosting and analytics | Respective providers | Terms, data-processing agreement, subprocessor list, data location, retention and security review | **Review required before connection** |
| Contributions from external developers or AI-assisted tools | Actual author / contributor and applicable service terms | Human contribution record, contract/assignment, applicable tool terms, third-party material review | **Record and review each contribution** |

## Mandatory release controls

1. Maintain a restricted evidence file for every assignment, licence, consent, permission and legal review. Do not commit confidential contracts or personal information to this repository.
2. Record asset path, version, SHA-256, creator, creation date, claimed owner, evidence reference, licence scope, reviewer and next review date.
3. Keep STN-owned materials under the proprietary all-rights-reserved notice unless an authorised STN representative approves a separate written licence.
4. Preserve third-party copyright, attribution and licence texts. Do not imply the STN proprietary notice overrides third-party terms.
5. Generate a software bill of materials (SBOM) and dependency licence report for each release candidate, including transitive dependencies and packaged assets.
6. Run dependency vulnerability, secret and licence-policy checks in CI. Review and document any copyleft, source-disclosure, attribution, notice, patent or redistribution obligations before distribution.
7. Block release of an instrument or protected item wording if digital use, reproduction, translation, scoring, storage, export, population or commercial permissions are unclear.
8. Do not treat public access to an instrument, questionnaire or logo as permission to reproduce or commercialise it.
9. Review external API, hosting, analytics and AI service terms for data processing, privacy, security, retention and cross-border transfers before enabling them.
10. Obtain New Zealand legal review of ownership, assignments, trademark position and the final third-party rights position before public distribution or commercial licensing.

## Required evidence fields

For every register entry retain:
- Exact asset / component name, repository path, version and SHA-256 where applicable.
- Creator(s), contributor(s), source, creation date and provenance.
- Current rights holder and basis for that conclusion.
- Assignment, employment/contract clause, licence or permission reference.
- Permitted use: display, reproduction, modification, translation, storage, export, distribution, sublicensing and commercial use.
- Territory, term, expiry, attribution, fee and other conditions.
- Third-party notices and licence text location.
- Reviewer, evidence date, next review date and unresolved restrictions.

## Current legal position

The repository's `LICENSE` and `COPYRIGHT.md` express a proprietary notice for STN-owned material and correctly preserve third-party rights. They do not prove that all material in the repository is owned by STN, nor do they grant rights over third-party instruments, software, fonts, icons or imagery.

**No blanket statement that all copyright and licences are cleared is authorised by this register.** Clearance is complete only when each relevant row has supporting evidence, all notices are included, and the release-specific SBOM/licence review is recorded.
