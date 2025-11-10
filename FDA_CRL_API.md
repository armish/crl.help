# FDA Complete Response Letters (CRL) API Documentation

## Table of Contents
- [Overview](#overview)
- [What are Complete Response Letters?](#what-are-complete-response-letters)
- [Why This Matters](#why-this-matters)
- [API Access](#api-access)
- [Data Structure](#data-structure)
- [Query Syntax](#query-syntax)
- [Examples](#examples)
- [Data Coverage & Limitations](#data-coverage--limitations)

---

## Overview

The FDA Complete Response Letters API provides public access to correspondence regarding New Drug Applications (NDAs) and Biologics License Applications (BLAs). This transparency initiative, launched on July 10, 2025, represents a major shift in FDA operations toward radical transparency.

**Key Statistics:**
- **Total Letters**: 392 (as of November 6, 2025)
- **Approved Applications**: 295
- **Unapproved Applications**: 97
- **Time Coverage**: 2020-2024

---

## What are Complete Response Letters?

Complete Response Letters (CRLs) are decision letters issued by the FDA when it completes its review of a drug or biological product application but **cannot grant approval in its current form**.

**Common reasons for CRLs:**
- Safety and efficacy concerns
- Manufacturing deficiencies
- Bioequivalence issues
- Prescribing information/labeling deficiencies
- Incomplete safety data

The letters detail:
- Specific deficiencies that must be addressed
- FDA recommendations for resolving issues
- Required resubmission timeline (typically within one year)

---

## Why This Matters

### FDA's Transparency Initiative

Previously, pharmaceutical sponsors often minimized or omitted FDA concerns when publicly announcing application rejections. A 2015 FDA analysis found that sponsors avoided mentioning **85% of the FDA's concerns about safety and efficacy** in their public disclosures.

### Benefits of Public CRLs:
1. **Industry Learning**: Companies can learn from others' mistakes rather than repeating them
2. **Predictability**: Better understanding of FDA expectations
3. **Faster Development**: Clear guidance accelerates getting treatments to patients
4. **Public Trust**: Transparency in the drug approval process

### Important Caveats:
- Letters are redacted to protect trade secrets and confidential commercial information (CCI) per FOIA regulations
- Data has not been validated for clinical or production use
- Should not be used to make medical care decisions

---

## API Access

### Base Endpoint
```
https://api.fda.gov/transparency/crl.json
```

### Authentication
No API key required (public access)

### Rate Limits
Not specified in documentation (standard openFDA limits likely apply)

### Alternative Access Methods

**Bulk Downloads:**
- Approved CRLs: `https://download.open.fda.gov/approved_CRLs.zip`
- Unapproved CRLs: `https://download.open.fda.gov/unapproved_CRLs.zip`

**Interactive Search:**
- Web interface: `https://open.fda.gov/crltable/`

---

## Data Structure

### Response Format

All API responses contain two main sections:

```json
{
  "meta": {
    "disclaimer": "...",
    "terms": "https://open.fda.gov/terms/",
    "license": "https://open.fda.gov/license/",
    "last_updated": "2025-11-06",
    "results": {
      "skip": 0,
      "limit": 1,
      "total": 392
    }
  },
  "results": [...]
}
```

### Available Fields

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `letter_date` | String | Date the letter was issued | "04/25/2025" |
| `letter_year` | String | Year of the letter | "2025" |
| `letter_type` | String | Type of letter | "COMPLETE RESPONSE" |
| `file_name` | String | PDF filename | "CRL_NDA215818_20250425.pdf" |
| `approval_status` | String | Current status | "Approved" or "Unapproved" |
| `application_number` | Array | FDA application number(s) | ["NDA 215818"] |
| `company_name` | String | Applicant company name | "Fresenius Kabi USA, LLC" |
| `company_address` | String | Company mailing address | "Three Corporate Drive\nLake Zurich, IL 60047" |
| `company_rep` | String | Company representative | "Jennifer Gross, MS" |
| `approver_name` | String | Approving organization | "U.S. Food and Drug Administration" |
| `approver_center` | Array | FDA center(s) involved | ["Center for Drug Evaluation and Research"] |
| `approver_title` | String | Approver location | "Silver Spring, MD 20993" |
| `text` | String | Full text content of the letter | (lengthy text) |

---

## Query Syntax

### Basic Query Structure

All queries use URL parameters joined by `&`:

```
https://api.fda.gov/transparency/crl.json?<parameter>=<value>&<parameter>=<value>
```

### Search Operations

**Single Field Search:**
```
search=field:term
```

**Boolean AND** (both conditions must match):
```
search=field1:term1+AND+field2:term2
```

**Boolean OR** (either condition matches):
```
search=field1:term1+field2:term2
```

**Phrase Matching** (exact phrase):
```
search=field:"exact phrase"
```

**Exact Field Matching:**
```
search=field.exact:"whole phrase"
```

### Pagination

**Limit results:**
```
limit=25
```

**Skip results (offset):**
```
skip=50
```

### Counting & Aggregation

**Count unique values:**
```
count=field_name
```

**Count exact phrases:**
```
count=field_name.exact
```

### Sorting

**Sort results:**
```
sort=field_name:desc    # descending
sort=field_name:asc     # ascending
```

---

## Examples

### 1. Get First Record
```
GET https://api.fda.gov/transparency/crl.json?limit=1
```

### 2. Search by Approval Status
```
GET https://api.fda.gov/transparency/crl.json?search=approval_status:unapproved&limit=10
```

### 3. Search by Company Name
```
GET https://api.fda.gov/transparency/crl.json?search=company_name:"Pfizer"&limit=5
```

### 4. Search by Year
```
GET https://api.fda.gov/transparency/crl.json?search=letter_year:2024&limit=20
```

### 5. Complex Search (AND operator)
```
GET https://api.fda.gov/transparency/crl.json?search=approval_status:unapproved+AND+letter_year:2024&limit=10
```

### 6. Count by Approval Status
```
GET https://api.fda.gov/transparency/crl.json?count=approval_status
```
**Response:**
```json
{
  "results": [
    {"term": "approved", "count": 295},
    {"term": "unapproved", "count": 97}
  ]
}
```

### 7. Count by FDA Center
```
GET https://api.fda.gov/transparency/crl.json?count=approver_center.exact
```

### 8. Search with Pagination
```
GET https://api.fda.gov/transparency/crl.json?search=letter_year:2023&limit=25&skip=0
```

### 9. Search Text Content
```
GET https://api.fda.gov/transparency/crl.json?search=text:"manufacturing deficiency"&limit=5
```

### 10. Multiple Criteria with OR
```
GET https://api.fda.gov/transparency/crl.json?search=letter_year:2023+letter_year:2024&limit=10
```

---

## Data Coverage & Limitations

### Coverage
- **Time Period**: Applications from 2020-2024
- **Application Types**: NDAs (New Drug Applications) and BLAs (Biologics License Applications)
- **Total Documents**: 392 letters (as of November 6, 2025)
- **Update Frequency**: Infrequent updates; FDA continues to publish archived CRLs

### Limitations

**Redactions:**
- Trade secrets removed per FOIA regulations
- Confidential commercial information (CCI) protected
- Some sections may show "(b)(4)" redaction markers

**Data Validation:**
- Not validated for clinical or production use
- Should not be relied upon for medical care decisions
- Informational purposes only

**API Constraints:**
- No real-time updates
- Historical data only (2020-2024)
- Some fields may contain redacted or incomplete information

### Important Disclaimers

From FDA documentation:
> "Do not rely on openFDA to make decisions regarding medical care. While we make every effort to ensure that data is accurate, you should assume all results are unvalidated."

---

## Example Response

```json
{
  "meta": {
    "disclaimer": "Do not rely on openFDA to make decisions regarding medical care...",
    "terms": "https://open.fda.gov/terms/",
    "license": "https://open.fda.gov/license/",
    "last_updated": "2025-11-06",
    "results": {
      "skip": 0,
      "limit": 1,
      "total": 392
    }
  },
  "results": [
    {
      "letter_date": "04/25/2025",
      "approver_title": "Silver Spring, MD 20993",
      "file_name": "CRL_NDA215818_20250425.pdf",
      "letter_year": "2025",
      "approval_status": "Unapproved",
      "approver_name": "U.S. Food and Drug Administration",
      "approver_center": [
        "Center for Drug Evaluation and Research"
      ],
      "company_rep": "Jennifer Gross, MS",
      "company_address": "Three Corporate Drive\nLake Zurich, IL 60047",
      "company_name": "Fresenius Kabi USA, LLC",
      "text": "[Full letter content - typically several paragraphs describing deficiencies and required actions]",
      "application_number": [
        "NDA 215818"
      ],
      "letter_type": "COMPLETE RESPONSE"
    }
  ]
}
```

---

## Technical Implementation Notes

### API Technology
- Built on Elasticsearch
- Returns JSON format by default
- RESTful API design

### Best Practices
1. **Use pagination** for large result sets (limit + skip)
2. **Use count endpoint** for statistics before fetching full results
3. **Cache responses** when appropriate (data updates infrequently)
4. **Handle redactions** in text field - expect "(b)(4)" markers
5. **Validate data** - don't assume completeness or accuracy for critical decisions

### Common Use Cases
- Researching FDA rejection patterns
- Understanding common deficiencies by therapeutic area
- Tracking specific companies' application histories
- Analyzing trends in FDA requirements over time
- Educational/academic research on drug approval process

---

## Additional Resources

- **FDA Press Release**: https://www.fda.gov/news-events/press-announcements/fda-embraces-radical-transparency-publishing-complete-response-letters
- **OpenFDA Main Site**: https://open.fda.gov/
- **Interactive CRL Search**: https://open.fda.gov/crltable/
- **API Documentation**: https://open.fda.gov/apis/transparency/completeresponseletters/
- **Terms of Service**: https://open.fda.gov/terms/
- **Data License**: https://open.fda.gov/license/

---

*Last Updated: November 9, 2025*
