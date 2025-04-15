# CV Generator Google Cloud Function

A Google Cloud Function (Gen 2) that generates professional CVs from templates based on structured data, with support for customization features such as section ordering, visibility controls, and anonymization.

## Features

- **Template-Based CV Generation**: Uses Jinja2-style DOCX templates
- **Multiple Output Formats**: Supports both DOCX and PDF outputs
- **CV Customization**:
  - Section ordering for customized CV layouts
  - Section visibility to show/hide specific CV sections
  - Anonymization option to mask personal information
- **Recruiter Branding**: Add agency and recruiter details to generated CVs
- **Secure Storage**: Uses Google Cloud Storage for templates and generated CVs
- **Strong Validation**: Pydantic-based request validation

## Setup

### Prerequisites

- Google Cloud Platform account
- Google Cloud CLI installed
- Python 3.9+

### Environment Variables

The function requires the following environment variables:

```
PROJECT_ID=your-gcp-project-id
STORAGE_BUCKET_NAME=your-storage-bucket
PROFILE=profile.json
PDF_CONVERSION_ENDPOINT=https://docx2pdf.tombrown.io/convert
PDF_API_KEY_SECRET=pdf-api-key
```

### GCP Service Setup

1. Create a Google Cloud Storage bucket:
```
gsutil mb -l LOCATION gs://BUCKET_NAME
```

2. Create folders in the bucket:
```
gsutil mkdir gs://BUCKET_NAME/cv-generator
gsutil mkdir gs://BUCKET_NAME/cv-schemas
gsutil mkdir gs://BUCKET_NAME/generated-cvs
```

3. Upload templates and schemas:
```
gsutil cp template_WIP.docx gs://BUCKET_NAME/cv-generator/
gsutil cp cv_schema.json gs://BUCKET_NAME/cv-schemas/
```

4. Create a profile configuration:
```json
{
  "schema": "cv_schema.json",
  "template": "template_WIP.docx",
  "agency_name": "Hireable Recruiting",
  "agency_logo": "agency_logo.png",
  "default_section_visibility": {
    "personal_info": true,
    "profile_statement": true,
    "skills": true,
    "experience": true,
    "education": true,
    "certifications": true,
    "achievements": true,
    "languages": true,
    "professional_memberships": true,
    "earlier_career": true,
    "publications": true,
    "additional_details": true
  },
  "default_section_order": {
    "sections": [
      "personal_info",
      "profile_statement",
      "skills",
      "experience",
      "education",
      "certifications",
      "achievements",
      "languages",
      "professional_memberships",
      "earlier_career",
      "publications",
      "additional_details"
    ]
  }
}
```

## Deployment

Deploy the function to Google Cloud:

```bash
gcloud functions deploy generate-cv \
  --gen2 \
  --runtime=python310 \
  --region=REGION \
  --source=. \
  --entry-point=generate_cv \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=300s \
  --set-env-vars PROJECT_ID=your-gcp-project-id,STORAGE_BUCKET_NAME=your-storage-bucket,PROFILE=profile.json
```

## API Usage

### Request Format

```json
{
  "template": "template_WIP.docx",
  "outputFormat": "pdf",
  "sectionOrder": [
    "personal_info",
    "profile_statement",
    "skills",
    "experience",
    "education"
  ],
  "sectionVisibility": {
    "personal_info": true,
    "profile_statement": true,
    "skills": true,
    "experience": true,
    "education": true,
    "certifications": false,
    "achievements": true
  },
  "isAnonymized": false,
  "recruiterProfile": {
    "firstName": "Jane",
    "lastName": "Smith",
    "email": "jane.smith@example.com",
    "phone": "+44 1234 567890",
    "agencyName": "Hireable Recruiting",
    "agencyLogo": "https://example.com/logo.png",
    "website": "https://example.com"
  },
  "data": {
    "firstName": "John",
    "surname": "Doe",
    "email": "john.doe@example.com",
    "phone": "+44 9876 543210",
    "address": "London, UK",
    "linkedin": "linkedin.com/in/johndoe",
    "profileStatement": "Experienced software engineer with 10+ years in full-stack development...",
    "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
    "experience": [
      {
        "role": "Senior Developer",
        "company": "Tech Solutions Ltd",
        "startDate": "2018-01",
        "endDate": "2023-05",
        "description": "Led development team in creating scalable applications..."
      }
    ],
    "education": [
      {
        "institution": "University of Technology",
        "degree": "BSc Computer Science",
        "startDate": "2013",
        "endDate": "2017",
        "grade": "First Class Honours"
      }
    ]
  }
}
```

### Response Format

```json
{
  "url": "https://storage.googleapis.com/your-bucket/generated-cvs/John Doe CV 2023-07-01-12-34-56.pdf?X-Goog-Signature=..."
}
```

## Integration

This function is designed to work with the Hireable CV Branding Buddy frontend application and the CV Parser backend. 